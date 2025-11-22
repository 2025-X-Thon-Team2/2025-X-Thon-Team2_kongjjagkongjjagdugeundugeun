import os
import json
import base64
from flask import Flask, request, jsonify, render_template
from PIL import Image
import google.generativeai as genai
from openai import OpenAI
from dotenv import load_dotenv # .env 파일 로드를 위한 라이브러리

# .env 파일에서 환경 변수를 로드합니다.
# 이 코드는 GOOGLE_API_KEY와 OPENAI_API_KEY 변수를 읽어옵니다.
load_dotenv()

# =======================================================
# Flask 애플리케이션 초기화
# =======================================================
app = Flask(__name__, template_folder='../frontend', static_folder='../frontend/static')

# =======================================================
# [설정] 환경 변수 및 상수
# =======================================================
# API 키를 환경 변수에서 불러오는 것이 가장 안전합니다. 
# 코드를 GitHub 등에 올릴 때 실제 키가 노출되지 않도록 합니다.
# os.environ.get()을 사용하면 환경 변수가 설정되지 않았을 때 기본값("YOUR_...")을 사용하여 오류를 방지할 수 있습니다.
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "YOUR_GOOGLE_API_KEY") # Google Gemini API 키
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY") # OpenAI GPT API 키

PROJECT_ID = "team_hackathon_demo" # 프로젝트 식별자
DB_FILE = "project_db.json"       # 점수 데이터베이스 파일명

# =======================================================
# [프롬프트 엔지니어링] 시스템 프롬프트
# =======================================================
# 각 AI 모델의 역할을 정의하는 프롬프트입니다. 이 프롬프트는 AI에게 어떤 역할을 수행해야 하는지 지시합니다.

# 1. GPT (Solver) 초기 페르소나: 문제를 해결하는 역할
PROMPT_SOLVER_INIT = """
You are a Distinguished Professor of Mathematics and Logic.
Your goal is to provide a flawless, step-by-step solution to the problem presented in the user's image.
**Instructions:**
1. Analyze the image carefully. Pay attention to numbers, symbols, and context.
2. Show your work clearly (Step-by-step reasoning).
3. If the image contains multiple questions, focus on the specific one requested.
4. Conclude with a definitive final answer.
**Output Format:**
- Use Markdown formatting.
- End your response with a clear block:
  `### Final Answer: [Your Result Here]`
"""

# 2. Gemini (Verifier) 검증 페르소나: GPT의 답변을 검증하는 역할
PROMPT_VERIFIER_INIT = """
You are the Chief Auditor of a high-stakes academic journal.
Your job is to ruthlessly verify the solution provided by 'Model 01' (The Solver) against the provided image.
**Your Task:**
1. Compare Model 01's answer with the image content.
2. Check for:
   - Hallucinations (Numbers/Symbols not in the image).
   - Calculation errors.
   - Logical fallacies.
**Output Rules (Strictly Follow):**
- If the solution is 100% correct, output ONLY: "VERDICT: CORRECT"
- If there is ANY error, output exactly in this format:
  VERDICT: INCORRECT
  ## Critique
  (Explain exactly what is wrong. Be specific.)
  ## Correct Solution
  (Provide the correct step-by-step solution and the final answer.)
"""

# 3. GPT (Solver) 방어/수정 페르소나: Gemini의 비평에 대해 방어하거나 수정하는 역할
PROMPT_SOLVER_DEFENSE = """
You are in a high-stakes debate. The 'Chief Auditor' (Gemini) has criticized your previous solution.
**Your Task:**
1. Review the Auditor's critique carefully.
2. **Self-Correction:** If the critic is right, admit it immediately. Say "I ADMIT" and provide the corrected solution.
3. **Defense:** If you are certain the critic is wrong (e.g., they misread the image), defend your stance. Say "I REBUT" and explain why your original logic holds.
**Output Format:**
- Start your response with either `[DECISION]: ADMIT` or `[DECISION]: REBUT`.
- Then provide your reasoning or corrected solution.
"""

# 4. Gemini (Verifier) 재검증 페르소나: GPT의 방어/수정 답변을 재검증하는 역할
PROMPT_VERIFIER_REBUTTAL = """
The Solver has responded to your critique.
If they admitted the error, confirm it. If they rebutted, evaluate their defense.
**Output Rules:**
- If they admitted and fixed it correctly, say: "VERDICT: RESOLVED (Winner: Gemini)"
- If they defended and convinced you, say: "VERDICT: CONCEDED (Winner: GPT)"
- If they are still wrong, say: "VERDICT: REJECTED" and state the final correct answer again.
"""

# =======================================================
# [함수] 데이터베이스 및 유틸리티
# =======================================================
# 프로젝트 점수를 로드하는 함수
def load_project_scores(project_id):
    if not os.path.exists(DB_FILE): 
        return {"GPT": 0, "Gemini": 0}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get(project_id, {"GPT": 0, "Gemini": 0})
    except: 
        # 파일 손상 등 예외 발생 시 기본 점수 반환
        return {"GPT": 0, "Gemini": 0}

# 프로젝트 점수를 저장하는 함수
def save_project_scores(project_id, scores):
    data = {}
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: 
                data = json.load(f)
        except: 
            pass # 파일이 있지만 읽을 수 없으면 무시하고 새 데이터로 덮어씀
    data[project_id] = scores
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False) # JSON 파일을 예쁘게(indent=4) 저장합니다.

# 토론 깊이에 따른 점수 계산 함수 (메르센 수 규칙)
def get_score_by_depth(loop_count, winner_role):
    if winner_role == "Gemini": 
        return (2 ** (loop_count * 2 - 1)) - 1
    else: 
        return (2 ** (loop_count * 2)) - 1

# =======================================================
# [핵심 로직] AI 분석 및 토론 과정
# 이 함수는 사용자가 업로드한 이미지와 질문을 바탕으로 GPT와 Gemini가 토론하며 문제를 해결하는 핵심 로직입니다.
# =======================================================
def run_analysis_logic(image_file, user_question):
    # --- 실제 API 연동 및 비즈니스 로직 구현을 위한 가이드라인 ---
    # 이 부분은 현재 프로토타입이며, 실제 서비스 구현 시 아래 사항들을 고려해야 합니다.
    # 
    # 1. 입력 유효성 검사 (Input Validation):
    #    - image_file이 유효한 이미지 파일인지 (예: 파일 형식, 크기 제한).
    #    - user_question이 비어있지 않은지, 부적절한 내용이 없는지.
    #    - 필요한 경우, 이미지 전처리(크기 조정, 압축 등)를 여기서 수행할 수 있습니다.
    # 
    # 2. 비동기 처리 (Asynchronous Processing):
    #    - AI 모델 호출은 시간이 오래 걸릴 수 있으므로, Flask 앱이 블로킹되지 않도록 비동기적으로 처리하는 것을 고려해야 합니다.
    #    - Celery, RQ 등의 큐 시스템을 사용하여 백그라운드에서 AI 작업을 처리하고, 프론트엔드에는 작업 ID를 반환한 뒤
    #      폴링(Polling) 또는 WebSocket을 통해 결과를 전달하는 방식이 일반적입니다.
    # 
    # 3. 에러 핸들링 및 로깅 (Error Handling & Logging):
    #    - AI API 호출 실패, 네트워크 오류, 데이터 처리 중 에러 등 다양한 예외 상황을 상세히 처리하고 로그를 남겨야 합니다.
    #    - 사용자에게는 친절하고 일반적인 오류 메시지를, 개발자에게는 상세한 오류 정보를 제공해야 합니다.
    # 
    # 4. 비용 관리 (Cost Management):
    #    - AI API 사용에는 비용이 발생하므로, 불필요한 호출을 줄이거나 사용량을 모니터링하는 로직이 필요할 수 있습니다.
    # 
    # 5. 확장성 및 모듈화 (Scalability & Modularity):
    #    - 현재는 모든 로직이 한 함수에 있지만, 실제 서비스에서는 각 AI 모델 호출, 점수 계산, 데이터 저장 등을 별도의 모듈/서비스로 분리하여
    #      코드의 가독성, 유지보수성, 확장성을 높여야 합니다. 특히 프롬프트는 별도 파일로 관리하거나 데이터베이스에 저장하는 것을 고려할 수 있습니다.
    # 
    # 6. 보안 (Security):
    #    - API 키는 절대 코드에 하드코딩하지 않고 환경 변수나 보안 저장소를 통해 관리해야 합니다. (현재 구현은 이를 따르고 있습니다.)
    #    - 사용자 입력에 대한 XSS(Cross-Site Scripting) 방어 등 웹 보안 원칙을 준수해야 합니다. (프론트엔드에서 기본적인 이스케이프 처리가 되어 있습니다.)
    # --- 가이드라인 끝 ---

    # API 키 설정 (Google Gemini)
    genai.configure(api_key=GOOGLE_API_KEY)
    
    # AI 클라이언트 초기화
    gemini_model = genai.GenerativeModel('gemini-1.5-flash') # Gemini 모델 로드
    client_gpt = OpenAI(api_key=OPENAI_API_KEY)             # OpenAI 클라이언트 초기화
    
    # 현재 프로젝트의 점수를 로드합니다.
    credit_scores = load_project_scores(PROJECT_ID)

    # 1. GPT 초기 솔루션 생성
    # 이미지 파일을 base64로 인코딩하여 AI 모델에 전달합니다.
    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    response_01 = client_gpt.chat.completions.create(
        model="gpt-4o", # 사용할 GPT 모델 지정
        messages=[
            {"role": "system", "content": PROMPT_SOLVER_INIT}, # 시스템 프롬프트
            {"role": "user", "content": [ # 사용자 질문과 이미지
                {"type": "text", "text": user_question},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]}
        ]
    )
    a01 = response_01.choices[0].message.content # GPT의 첫 번째 답변

    # 2. Gemini 검증
    image_file.seek(0) # PIL(Pillow)이 이미지 파일을 다시 읽을 수 있도록 파일 포인터를 처음으로 되돌립니다.
    pil_image = Image.open(image_file) # 이미지 파일을 PIL 객체로 로드
    response_02 = gemini_model.generate_content(
        [PROMPT_VERIFIER_INIT, f"User Question: {user_question}\n\nModel 01 Solution:\n{a01}", pil_image] # Gemini에게 검증 프롬프트와 GPT 답변 전달
    )
    r02 = response_02.text # Gemini의 검증 결과 (비평 또는 CORRECT)
    
    is_correct = "VERDICT: CORRECT" in r02 # Gemini가 'CORRECT'라고 판단했는지 확인
    
    # 3. AI 토론 해결 루프
    final_answer = "" # 최종 답변
    winner = ""      # 최종 승자
    status_updates = [] # 토론 과정을 기록할 리스트
    status_updates.append({"model": "GPT", "content": a01, "step": "Initial Solution"}) # 초기 GPT 답변 기록
    status_updates.append({"model": "Gemini", "content": r02, "step": "Verification"}) # Gemini 검증 결과 기록

    if is_correct:
        # Gemini가 'CORRECT'라고 판단하면 토론 종료
        winner = "Draw (Agreement)"
        final_answer = a01
    else:
        # 'INCORRECT'라고 판단하면 토론 시작
        current_loop = 0    # 현재 토론 라운드
        max_loops = 3       # 최대 토론 라운드 수
        loop_active = True  # 토론 활성화 여부
        # Gemini의 비평 내용 추출
        current_critique = r02.replace("VERDICT: INCORRECT", "").strip()

        while loop_active and current_loop < max_loops: # 최대 라운드에 도달하거나 토론이 해결될 때까지 반복
            current_loop += 1
            
            # 3-1. GPT 방어 (Gemini의 비평에 대한 GPT의 답변)
            response_loop_gpt = client_gpt.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": PROMPT_SOLVER_DEFENSE},
                    {"role": "user", "content": f"Auditor's Critique:\n{current_critique}"}
                ]
            )
            gpt_defense = response_loop_gpt.choices[0].message.content # GPT의 방어/수정 답변
            status_updates.append({"model": "GPT", "content": gpt_defense, "step": f"Round {current_loop} Defense"})

            if "[DECISION]: ADMIT" in gpt_defense: # GPT가 오류를 인정하고 수정했다면
                points = get_score_by_depth(current_loop, "Gemini") # Gemini에게 점수 부여
                credit_scores["Gemini"] += points
                final_answer = gpt_defense.replace("[DECISION]: ADMIT", "").strip() # GPT의 수정된 답변을 최종 답변으로 채택
                winner = "Gemini"
                loop_active = False # 토론 종료
                break

            # 3-2. Gemini 재평가 (GPT의 방어에 대한 Gemini의 재검증)
            response_loop_gemini = gemini_model.generate_content(
                [PROMPT_VERIFIER_REBUTTAL, f"GPT Defense:\n{gpt_defense}", pil_image] # Gemini에게 재검증 프롬프트와 GPT 방어 전달
            )
            gemini_reaction = response_loop_gemini.text # Gemini의 재평가 결과
            status_updates.append({"model": "Gemini", "content": gemini_reaction, "step": f"Round {current_loop} Re-evaluation"})

            if "VERDICT: CONCEDED" in gemini_reaction: # Gemini가 GPT의 방어를 인정했다면 (GPT 승리)
                points = get_score_by_depth(current_loop, "GPT")
                credit_scores["GPT"] += points
                final_answer = gpt_defense.replace("[DECISION]: REBUT", "").strip()
                winner = "GPT"
                loop_active = False # 토론 종료
            elif "VERDICT: RESOLVED" in gemini_reaction: # GPT가 오류를 인정했고 Gemini가 확인했다면 (Gemini 승리)
                points = get_score_by_depth(current_loop, "Gemini")
                credit_scores["Gemini"] += points
                final_answer = gpt_defense
                winner = "Gemini"
                loop_active = False # 토론 종료
            else:
                # 여전히 합의에 도달하지 못했다면 토론 계속
                current_critique = gemini_reaction # Gemini의 새로운 비평으로 업데이트
                if current_loop == max_loops: # 최대 라운드에 도달하면
                    # 점수를 바탕으로 최종 승자 결정
                    score_gpt = credit_scores["GPT"]
                    score_gemini = credit_scores["Gemini"]
                    if score_gpt >= score_gemini:
                        winner = f"GPT (Credit Win: {score_gpt} vs {score_gemini})"
                        final_answer = a01 # 신뢰도 높은 초기 GPT 답변 채택
                    else:
                        winner = f"Gemini (Credit Win: {score_gemini} vs {score_gpt})"
                        final_answer = current_critique # Gemini의 마지막 비평 (내부에 정답이 있을 것으로 가정)
                    loop_active = False # 토론 종료
    
    # 최종 점수 저장
    save_project_scores(PROJECT_ID, credit_scores)
    
    # 최종 결과 반환
    return {
        "winner": winner,
        "final_answer": final_answer,
        "scores": credit_scores,
        "process": status_updates # 토론 과정 반환 (프론트엔드에서 타임라인으로 표시)
    }

# =======================================================
# [API 라우트] 웹 페이지 및 API 엔드포인트
# =======================================================
# 기본 경로 ('/')로 접속 시 frontend/index.html 파일을 렌더링하여 반환합니다.
@app.route('/')
def index():
    return render_template('index.html')

# 이미지 업로드 및 AI 분석을 처리하는 API 엔드포인트 ('/api/solve')
# POST 요청만 허용합니다.
@app.route('/api/solve', methods=['POST'])
def solve_problem():
    # 요청에 'image' 파일이 포함되어 있는지 확인합니다.
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400 # 400 Bad Request 에러 반환
    
    image_file = request.files['image'] # 업로드된 이미지 파일 가져오기
    # 'question' 폼 데이터를 가져옵니다. 기본 질문도 설정할 수 있습니다.
    user_question = request.form.get('question', 'Please solve the problem in the image.')

    # 파일 이름이 비어있는지 확인합니다.
    if image_file.filename == '':
        return jsonify({"error": "No selected file"}), 400 # 400 Bad Request 에러 반환

    try:
        # 핵심 AI 분석 로직 함수 호출
        result = run_analysis_logic(image_file, user_question)
        return jsonify(result) # 분석 결과를 JSON 형태로 반환
    except Exception as e:
        # 예외 발생 시 에러를 기록하고 500 Internal Server Error를 반환합니다.
        # 프로덕션 환경에서는 사용자에게 상세한 에러 메시지를 노출하지 않도록 주의해야 합니다.
        print(f"Error processing request: {e}") # 개발을 위한 에러 로그
        return jsonify({"error": "An unexpected error occurred."}), 500

# =======================================================
# [애플리케이션 실행]
# =======================================================
if __name__ == '__main__':
    # Flask 개발 서버를 실행합니다.
    # debug=True는 개발 중에 유용하며, 코드 변경 시 서버가 자동으로 재시작됩니다. (프로덕션에서는 사용 금지)
    # port=5000은 서버가 5000번 포트에서 실행되도록 합니다.
    app.run(debug=True, port=5000)

