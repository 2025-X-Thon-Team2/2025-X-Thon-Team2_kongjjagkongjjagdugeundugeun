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
# [Prompt Engineering] System Prompts (English & Citation-Aware)
# =======================================================
# New prompt for Gemini to pre-analyze the user's request.
PROMPT_PRE_ANALYZER = """
You are a senior analyst. Your task is to thoroughly analyze the user's image and question to extract key information before the main solver begins.
**Instructions:**
1.  **Analyze the Image:** Identify the core subject (e.g., math, physics, logic puzzle).
2.  **Identify the Goal:** What is the user's ultimate question?
3.  **Extract Key Data:** List all relevant numbers, variables, and conditions shown in the image.
4.  **Formulate a Plan:** Outline the steps a solver should take to answer the question.
**Output Format (Strictly follow):**
- **Subject:** [e.g., Algebra]
- **Goal:** [e.g., Solve for the variable 'x']
- **Key Data:** [e.g., Equation: 2x + 5 = 15, Condition: x must be a positive integer]
- **Action Plan:**
    1. [First step]
    2. [Second step]
    3. [Third step]
"""

# 1. GPT (Solver) - Modified to require sources.
PROMPT_SOLVER_INIT = """
You are a Distinguished Professor of Mathematics and Logic. Your goal is to provide a flawless, step-by-step solution in **English**.
**Analysis from a pre-check is provided below, use it for your reference.**
---
{pre_analysis_result}
---
**Instructions:**
1.  Provide a clear, step-by-step reasoning for your solution.
2.  **You MUST cite a credible source** for the primary theorem, formula, or method used. This source can be a well-known academic website (e.g., Wolfram MathWorld, Khan Academy) or a published paper.
3.  Conclude with a definitive final answer.
**Output Format (Strictly follow):**
## Step-by-Step Solution
(Your detailed solution here)

### Source
- **Method/Theorem:** [e.g., Pythagorean theorem]
- **Citation:** [Provide a URL or reference to the source]

### Final Answer
[Your Result Here]
"""

# 2. Gemini (Verifier) - Modified to verify the source.
PROMPT_VERIFIER_INIT = """
You are the Chief Auditor of a high-stakes academic journal. Your job is to ruthlessly verify the solution provided by 'Model 01' (The Solver) in **English**.
**Your Task:**
1.  **Verify the Solution:** Check the step-by-step solution for calculation errors, logical fallacies, or hallucinations.
2.  **Verify the Source:**
    - Examine the cited source.
    - Does the source support the method/theorem claimed?
    - Is the source credible?
**Output Rules (Strictly Follow):**
- If the solution AND the source are 100% correct and credible, output ONLY: "VERDICT: CORRECT"
- If there is ANY error (in the solution OR the source), output exactly in this format:
  VERDICT: INCORRECT
  ## Critique
  (Explain exactly what is wrong. Be specific about errors in the solution or issues with the source.)
  ## Correct Solution
  (Provide the correct step-by-step solution, a credible source, and the final answer.)
"""

# 3. GPT (Solver) Defense - Modified for English.
PROMPT_SOLVER_DEFENSE = """
You are in a high-stakes debate. The 'Chief Auditor' (Gemini) has criticized your previous solution. Your response must be in **English**.
**Your Task:**
1.  Review the Auditor's critique carefully.
2.  **Self-Correction:** If the critic is right, admit it. Start with `[DECISION]: ADMIT`, then provide the fully corrected solution, including a new or corrected source.
3.  **Defense:** If you are certain the critic is wrong, defend your stance. Start with `[DECISION]: REBUT` and explain why your original logic and source are correct.
"""

# 4. Gemini (Verifier) Rebuttal - Modified for English.
PROMPT_VERIFIER_REBUTTAL = """
The Solver has responded to your critique. Evaluate their response in **English**.
**Output Rules:**
- If they admitted and fixed the issue correctly: "VERDICT: RESOLVED (Winner: Gemini)"
- If they rebutted and you are now convinced: "VERDICT: CONCEDED (Winner: GPT)"
- If they are still wrong: "VERDICT: REJECTED" and restate the final correct answer and source.
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
# [Core Logic] AI Analysis and Debate Process (New Version)
# =======================================================
def run_analysis_logic(image_file, user_question):
    # --- Guideline Comments (Same as before) ---
    # ...

    # Configure APIs
    genai.configure(api_key=GOOGLE_API_KEY)
    client_gpt = OpenAI(api_key=OPENAI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
    
    credit_scores = load_project_scores(PROJECT_ID)
    status_updates = []

    # === New Step 0: Gemini Pre-analysis ===
    image_file.seek(0)
    pil_image = Image.open(image_file)
    pre_analysis_response = gemini_model.generate_content(
        [PROMPT_PRE_ANALYZER, user_question, pil_image]
    )
    pre_analysis_result = pre_analysis_response.text
    status_updates.append({"model": "Gemini", "content": pre_analysis_result, "step": "Pre-analysis"})

    # === Step 1: GPT Initial Solution ===
    image_file.seek(0)
    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    # Inject the pre-analysis result into the solver prompt
    solver_prompt = PROMPT_SOLVER_INIT.format(pre_analysis_result=pre_analysis_result)
    
    response_01 = client_gpt.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": solver_prompt},
            {"role": "user", "content": [
                {"type": "text", "text": user_question},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]}
        ]
    )
    a01 = response_01.choices[0].message.content
    status_updates.append({"model": "GPT", "content": a01, "step": "Initial Solution"})

    # === Step 2: Gemini Verification ===
    image_file.seek(0)
    pil_image = Image.open(image_file)
    response_02 = gemini_model.generate_content(
        [PROMPT_VERIFIER_INIT, f"User Question: {user_question}\n\nModel 01 Solution:\n{a01}", pil_image]
    )
    r02 = response_02.text
    status_updates.append({"model": "Gemini", "content": r02, "step": "Verification"})
    
    is_correct = "VERDICT: CORRECT" in r02
    
    # === Step 3: Conflict Resolution Loop ===
    final_answer = ""
    winner = ""

    if is_correct:
        winner = "Draw (Agreement)"
        final_answer = a01
    else:
        current_loop = 0
        max_loops = 3
        loop_active = True
        current_critique = r02.replace("VERDICT: INCORRECT", "").strip()

        while loop_active and current_loop < max_loops:
            current_loop += 1
            
            # 3-1. GPT Defense
            response_loop_gpt = client_gpt.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": PROMPT_SOLVER_DEFENSE},
                    {"role": "user", "content": f"Auditor's Critique:\n{current_critique}"}
                ]
            )
            gpt_defense = response_loop_gpt.choices[0].message.content
            status_updates.append({"model": "GPT", "content": gpt_defense, "step": f"Round {current_loop} Defense"})

            if "[DECISION]: ADMIT" in gpt_defense:
                points = get_score_by_depth(current_loop, "Gemini")
                credit_scores["Gemini"] += points
                final_answer = gpt_defense.replace("[DECISION]: ADMIT", "").strip()
                winner = "Gemini"
                loop_active = False
                break

            # 3-2. Gemini Re-evaluation
            response_loop_gemini = gemini_model.generate_content(
                [PROMPT_VERIFIER_REBUTTAL, f"GPT Defense:\n{gpt_defense}", pil_image]
            )
            gemini_reaction = response_loop_gemini.text
            status_updates.append({"model": "Gemini", "content": gemini_reaction, "step": f"Round {current_loop} Re-evaluation"})

            if "VERDICT: CONCEDED" in gemini_reaction:
                points = get_score_by_depth(current_loop, "GPT")
                credit_scores["GPT"] += points
                final_answer = gpt_defense.replace("[DECISION]: REBUT", "").strip()
                winner = "GPT"
                loop_active = False
            elif "VERDICT: RESOLVED" in gemini_reaction:
                points = get_score_by_depth(current_loop, "Gemini")
                credit_scores["Gemini"] += points
                final_answer = gpt_defense
                winner = "Gemini"
                loop_active = False
            else:
                current_critique = gemini_reaction
                if current_loop == max_loops:
                    score_gpt = credit_scores["GPT"]
                    score_gemini = credit_scores["Gemini"]
                    if score_gpt >= score_gemini:
                        winner = f"GPT (Credit Win: {score_gpt} vs {score_gemini})"
                        final_answer = a01
                    else:
                        winner = f"Gemini (Credit Win: {score_gemini} vs {score_gpt})"
                        final_answer = current_critique
                    loop_active = False
    
    save_project_scores(PROJECT_ID, credit_scores)
    
    return {
        "winner": winner,
        "final_answer": final_answer,
        "scores": credit_scores,
        "process": status_updates
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

