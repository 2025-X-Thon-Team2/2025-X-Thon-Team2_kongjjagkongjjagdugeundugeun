import os
import json
import base64
from flask import Flask, request, jsonify, render_template
from PIL import Image
import google.generativeai as genai
from openai import OpenAI
from dotenv import load_dotenv
from serpapi import GoogleSearch

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

# =======================================================
# Flask 애플리케이션 초기화
# =======================================================
app = Flask(__name__, template_folder='../frontend', static_folder='../frontend/static')

# =======================================================
# [설정] 환경 변수 및 상수
# =======================================================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "YOUR_GOOGLE_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")
SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY", "YOUR_SERPAPI_API_KEY")

PROJECT_ID = "team_hackathon_demo"
DB_FILE = "project_db.json"

# =======================================================
# [Prompt Engineering] System Prompts (Korean)
# =======================================================

# Step 1: Classify the subject from the image (Korean)
PROMPT_SUBJECT_CLASSIFIER = """
당신은 전문적인 학문 분야 분류기입니다. 사용자의 이미지와 질문을 분석하여 특정 학문 분야를 식별하는 임무를 맡았습니다.
**지침:**
1. 이미지의 기호, 다이어그램, 텍스트를 분석하세요.
2. 사용자의 질문을 분석하세요.
3. 가장 관련성이 높은 학문 분야의 이름("선형대수학", "미적분학", "물리학 I", "컴퓨터 구조", "자료구조" 등)만 출력하세요. 다른 텍스트나 설명은 추가하지 마세요.
"""

# Step 2: Generate search queries based on the subject (Korean)
PROMPT_KNOWLEDGE_CRAWLER_QUERIES = """
당신은 연구 보조원입니다. 식별된 주제를 바탕으로, 해당 분야의 문제를 해결하기 위한 필수 배경 지식을 수집하기 위해 3-4개의 간결한 Google 검색어를 생성하세요.
**주제:** {subject}
**지침:**
- 핵심 정의, 주요 공식, 기본 정리에 대한 검색어를 만드세요.
- 검색어만 한 줄에 하나씩 출력하세요.
**입력 예시:** "선형대수학"
**출력 예시:**
행렬식이란
역행렬 공식
고유값과 고유벡터 정의
선형 시스템 해결을 위한 크래머 법칙
"""

# Step 3: Generate a structured Knowledge Package from search results (Korean)
PROMPT_KNOWLEDGE_PACKAGE_GENERATOR = """
당신은 데이터 설계자입니다. 당신의 임무는 웹 검색에서 얻은 원시 텍스트를 처리하여 구조화된 JSON "지식 패키지"로 만드는 것입니다.
**규칙:**
- 출력은 반드시 단일의 유효한 JSON 객체여야 합니다.
- 제공된 검색 결과를 바탕으로 필드를 채우세요.
- `context_text`는 AI가 읽을 수 있도록 수집된 모든 정보의 간결한 요약이어야 하며, **한국어로 작성**되어야 합니다.

**원시 검색 결과:**
---
{search_results}
---

**JSON 출력 형식:**
{{
  "field": "{subject}",
  "symbols": ["..."],
  "formulas": ["..."],
  "definitions": ["..."],
  "examples": ["..."],
  "context_text": "{subject}와 관련된 핵심 개념, 공식, 정의에 대한 포괄적인 요약..."
}}
"""

# Step 4: The main solver prompt, now including the Knowledge Package (Korean)
PROMPT_SOLVER_INIT = """
당신은 세계적으로 저명한 교수입니다. 당신의 목표는 제공된 지식을 활용하여 완벽하고 단계적인 해결책을 **한국어로** 제공하는 것입니다.

**이 특정 분야에 대해 사전 패키징된 지식:**
---
{knowledge_package}
---

**지침:**
1. 해결책을 공식화하기 위해 제공된 "사전 패키징된 지식"에 크게 의존해야 합니다.
2. 명확하고 단계적인 추론을 제공하세요.
3. 지식 패키지나 당신의 지식에서 가져온 기본 정리나 공식에 대한 **신뢰할 수 있는 출처를 반드시 인용**해야 합니다.
4. **수식 서식:** 모든 수학적 표기법은 LaTeX를 사용하여 포맷하세요. 인라인 수식은 `\\(...\\)`로, 블록 수식은 `$$...$$`로 묶어주세요.
5. 명확한 최종 답변으로 마무리하세요.

**출력 형식 (엄격히 준수):**
## 단계별 해결책
(여기에 상세한 해결책)

### 출처
- **방법/정리:** [예: 크래머 법칙]
- **인용:** [출처에 대한 URL 또는 참조 제공]

### 최종 답변
[여기에 결과]
"""

# Prompts for the debate loop (Korean)
PROMPT_VERIFIER_INIT = """
당신은 매우 중요한 학술지의 최고 감사관입니다. 당신의 임무는 '해결사 모델'이 제공한 해결책을 **한국어로** 무자비하게 검증하는 것입니다.
**임무:**
1.  **해결책 검증:** 단계별 해결책의 계산 오류, 논리적 오류, 또는 환각(hallucination)을 확인하세요.
2.  **출처 검증:** 인용된 출처를 검토하고, 주장을 뒷받침하는지, 신뢰할 수 있는지 확인하세요.
3.  **수식 서식:** 당신의 답변에 포함된 모든 수학적 표기법은 LaTeX를 사용하여 포맷하세요. 인라인 수식은 `\\(...\\)`로, 블록 수식은 `$$...$$`로 묶어주세요.
**매우 중요:** 최종 답이 명백히 틀렸거나, 풀이 과정에 치명적인 논리적/계산 오류가 있는 경우에만 '오류'로 판정하세요. 사소한 표현 차이나 스타일은 문제 삼지 마세요.

**출력 규칙 (엄격히 준수):**
- **정답인 경우:** 당신의 방식으로 문제를 다시 풀어보고, 그 풀이 과정 끝에 "따라서 모델 01의 답변이 올바릅니다."라고 결론을 내리세요.
- **오류가 있는 경우:** "모델 01의 해결책에는 다음과 같은 오류가 있습니다." 라는 문장으로 시작하여, 구체적인 비판과 함께 올바른 해결책을 `## 올바른 해결책`이라는 제목 아래에 제시하세요.
"""

PROMPT_SOLVER_DEFENSE = """
당신은 중요한 토론에 참여하고 있습니다. '최고 감사관'(Gemini)이 당신의 이전 해결책을 비판했습니다. 당신의 답변은 **한국어로** 작성되어야 합니다.
**임무:**
1.  감사관의 비판을 신중하게 검토하세요.
2.  **수식 서식:** 당신의 답변에 포함된 모든 수학적 표기법은 LaTeX를 사용하여 포맷하세요. 인라인 수식은 `\\(...\\)`로, 블록 수식은 `$$...$$`로 묶어주세요.
3.  **자기 수정:** 비판이 옳다면, "검토 결과, 제 해결책에 오류가 있었음을 인정합니다."로 시작하여 오류의 원인을 설명한 후, 수정된 전체 풀이 과정과 답을 제시하세요.
4.  **방어:** 비판이 틀렸다고 확신한다면, 당신의 입장을 방어하세요. 왜 당신의 원래 논리와 출처가 정확한지 설명하는 내용만 제시하세요.
"""

PROMPT_VERIFIER_REBUTTAL = """
해결사가 당신의 비판에 답변했습니다. 그들의 응답을 **한국어로** 평가하세요.
**수식 서식:** 당신의 답변에 포함된 모든 수학적 표기법은 LaTeX를 사용하여 포맷하세요. 인라인 수식은 `\\(...\\)`로, 블록 수식은 `$$...$$`로 묶어주세요.

**출력 규칙:**
- 만약 그들이 문제를 인정하고 올바르게 수정했다면: "해결사의 수정을 검토한 결과, 이제 해결책이 정확함을 확인했습니다." 라는 문장으로 시작하세요.
- 만약 그들이 반박했고 당신이 이제 설득되었다면: "해결사의 반박을 검토한 결과, 제 지적이 틀렸으며 해결사의 원래 주장이 옳았음을 인정합니다." 라는 문장으로 시작하세요.
- 만약 그들이 여전히 틀렸다면: "해결사의 반박에도 불구하고, 여전히 원래 해결책에는 오류가 있습니다. 최종적으로 올바른 해결책은 다음과 같습니다." 라는 문장으로 시작하여 당신의 최종 해결책을 제시하세요.
"""

# =======================================================
# [Prompt Engineering] Debate Summary Prompts (Korean)
# =======================================================
PROMPT_DEBATE_SUMMARY = """
당신은 두 AI 모델 간의 토론을 분석하고 요약하는 전문가입니다. 제공된 정보를 바탕으로 다음 세 가지 항목을 정확히 추출하고, 반드시 한국어로 작성해주세요.

1.  **계산 근거 요약**: 최종 답안을 도출하기까지의 핵심적인 계산 과정이나 논리적 근거를 요약합니다.
2.  **GPT 초기 답변의 오류 포인트 3가지**: Gemini가 지적한 GPT의 초기 답변의 구체적인 오류 3가지를 목록 형태로 제시합니다.
3.  **Gemini의 검증 근거 3가지**: Gemini가 GPT의 오류를 찾아내기 위해 사용한 검증 논리나 근거 3가지를 목록 형태로 제시합니다.

**입력 정보:**
---
[GPT 초기 답변]
{a01}
---
[Gemini 검증 내용]
{r02}
---

**출력 규칙:**
- 반드시 다음의 JSON 형식을 사용하세요.
- 각 항목에 대해 3가지 포인트가 없는 경우, 가능한 만큼만 채우고 나머지는 비워두세요.

```json
{{
  "calculation_summary": "요약 내용...",
  "gpt_errors": [
    "오류 포인트 1",
    "오류 포인트 2",
    "오류 포인트 3"
  ],
  "gemini_verification": [
    "검증 근거 1",
    "검증 근거 2",
    "검증 근거 3"
  ]
}}
```
"""

PROMPT_DEBATE_CONCLUSION = """
당신은 AI 토론의 결과를 요약하는 최종 보고서 작성자입니다. 다음 정보를 바탕으로, 교차검증 결론을 2~3줄의 완결된 문장으로 요약해주세요. 반드시 한국어로 작성해야 합니다.

**정보:**
- **토론 승자:** {winner}
- **최종 결론:** {final_answer}

**요약 예시:**
초기 GPT 답변에서 몇 가지 오류가 발견되었으나, Gemini의 정밀한 교차검증을 통해 이를 바로잡았습니다. 최종적으로 Gemini가 제시한 수정된 해결책이 더 정확한 것으로 판명되어 최종 답안으로 채택되었습니다.
"""

# =======================================================
# [함수] 데이터베이스 및 유틸리티
# =======================================================
def load_project_scores(project_id):
    if not os.path.exists(DB_FILE): return {"GPT": 0, "Gemini": 0}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get(project_id, {"GPT": 0, "Gemini": 0})
    except: return {"GPT": 0, "Gemini": 0}

def save_project_scores(project_id, scores):
    data = {}
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: data = json.load(f)
        except: pass
    data[project_id] = scores
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def perform_google_search(query):
    try:
        search = GoogleSearch({"q": query, "api_key": SERPAPI_API_KEY})
        results = search.get_dict()
        
        if "error" in results:
            return f"Search Error: {results['error']}"

        snippets = []
        if "organic_results" in results:
            for result in results["organic_results"][:3]:
                snippet = result.get("snippet", "No snippet available.")
                link = result.get("link", "#")
                snippets.append(f"Title: {result.get('title', 'N/A')}\nSnippet: {snippet}\nSource: {link}")
        
        return "\n".join(snippets) if snippets else "검색 결과가 없습니다."
    except Exception as e:
        print(f"Error during Google Search: {e}")
        return f"검색 중 예외 발생: {str(e)}"

def format_final_summary(gemini_model, a01, r02, final_answer, winner, is_correct):
    summary_data = {
        "calculation_summary": "해당 없음",
        "gpt_errors": ["오류가 발견되지 않았습니다."],
        "gemini_verification": ["GPT의 초기 답변이 정확하여 추가 검증이 필요하지 않았습니다."]
    }

    if not is_correct:
        try:
            # 토론 요약 (계산 근거, 오류 포인트, 검증 근거)
            summary_prompt = PROMPT_DEBATE_SUMMARY.format(a01=a01, r02=r02)
            summary_response = gemini_model.generate_content([summary_prompt])
            
            # 응답에서 JSON 부분만 추출
            cleaned_json_string = summary_response.text.strip()
            if cleaned_json_string.startswith("```json"):
                cleaned_json_string = cleaned_json_string[len("```json"):].strip()
            if cleaned_json_string.endswith("```"):
                cleaned_json_string = cleaned_json_string[:-len("```")].strip()
            
            summary_json = json.loads(cleaned_json_string)
            summary_data.update(summary_json)
        except Exception as e:
            print(f"Error generating debate summary: {e}")
            # Fallback if parsing fails
            summary_data['gpt_errors'] = ["Gemini의 검증 내용에서 오류 포인트를 추출하는 데 실패했습니다."]
            summary_data['gemini_verification'] = [r02]


    # 최종 결론 요약
    conclusion_summary = ""
    try:
        conclusion_prompt = PROMPT_DEBATE_CONCLUSION.format(winner=winner, final_answer=final_answer)
        conclusion_response = gemini_model.generate_content([conclusion_prompt])
        conclusion_summary = conclusion_response.text.strip()
    except Exception as e:
        print(f"Error generating conclusion summary: {e}")
        conclusion_summary = "최종 결론을 요약하는 데 실패했습니다."

    # 최종 텍스트 포맷팅
    gpt_errors_formatted = "\n- ".join(summary_data.get('gpt_errors', ['추출 실패']))
    gemini_verification_formatted = "\n- ".join(summary_data.get('gemini_verification', ['추출 실패']))

    formatted_string = f"""
[1] 최종 답안
{final_answer}

[2] 계산 근거 요약
{summary_data.get('calculation_summary', '요약 실패')}

[3] GPT 초기 답변의 오류 포인트
- {gpt_errors_formatted}

[4] Gemini의 검증 근거
- {gemini_verification_formatted}

[5] 교차검증 결론 요약
{conclusion_summary}
"""
    return formatted_string.strip()

# =======================================================
# [Core Logic] AI Analysis and Debate Process (New Pipeline)
# =======================================================
def run_analysis_logic(project_id, image_file, user_question):
    genai.configure(api_key=GOOGLE_API_KEY)
    client_gpt = OpenAI(api_key=OPENAI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-2.5-pro')
    
    credit_scores = load_project_scores(project_id)
    status_updates = []
    
    image_file.seek(0)
    pil_image = Image.open(image_file)

    # === Step 1: Subject Classification ===
    subject_response = gemini_model.generate_content(
        [PROMPT_SUBJECT_CLASSIFIER, user_question, pil_image]
    )
    subject = subject_response.text.strip()
    status_updates.append({"model": "System", "content": f"인식된 주제: {subject}", "step": "주제 분류"})

    # === Step 2: Knowledge Crawling ===
    queries_prompt = PROMPT_KNOWLEDGE_CRAWLER_QUERIES.format(subject=subject)
    queries_response = gemini_model.generate_content([queries_prompt])
    search_queries = queries_response.text.strip().split('\n')
    
    raw_search_results = ""
    crawling_content = "생성된 검색어:\n" + "\n".join(search_queries) + "\n\n--- 검색 결과 ---\n"
    for query in search_queries:
        if query:
            results = perform_google_search(query)
            raw_search_results += f"'{query}'에 대한 결과:\n{results}\n\n"
    
    crawling_content += raw_search_results
    status_updates.append({"model": "System", "content": crawling_content, "step": "지식 수집"})

    # === Step 3: Knowledge Package Generation ===
    package_prompt = PROMPT_KNOWLEDGE_PACKAGE_GENERATOR.format(subject=subject, search_results=raw_search_results)
    package_response = gemini_model.generate_content([package_prompt])
    cleaned_json_string = package_response.text.strip().replace("```json", "").replace("```", "")
    knowledge_package_str = cleaned_json_string
    status_updates.append({"model": "System", "content": knowledge_package_str, "step": "지식 패키지 생성"})

    # === Step 4: GPT Initial Solution with Knowledge Injection ===
    image_file.seek(0)
    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    solver_prompt = PROMPT_SOLVER_INIT.format(knowledge_package=knowledge_package_str)
    
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
    status_updates.append({"model": "GPT", "content": a01, "step": "초기 해결책"})

    # === Step 5: Gemini Verification ===
    image_file.seek(0)
    pil_image_verify = Image.open(image_file)
    response_02 = gemini_model.generate_content(
        [PROMPT_VERIFIER_INIT, f"사용자 질문: {user_question}\n\n모델 01 해결책:\n{a01}", pil_image_verify]
    )
    r02 = response_02.text
    status_updates.append({"model": "Gemini", "content": r02, "step": "검증"})
    
    is_correct = "따라서 모델 01의 답변이 올바릅니다." in r02
    
    # === Step 6: Conflict Resolution Loop ===
    final_answer = ""
    winner = ""

    if is_correct:
        winner = "Draw (Agreement)"
        final_answer = a01
    else:
        current_loop = 0
        max_loops = 5
        loop_active = True
        current_critique = r02.replace("모델 01의 해결책에는 다음과 같은 오류가 있습니다.", "").strip()

        while loop_active and current_loop < max_loops:
            current_loop += 1
            
            response_loop_gpt = client_gpt.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": PROMPT_SOLVER_DEFENSE},
                    {"role": "user", "content": f"감사관의 비판:\n{current_critique}"}
                ]
            )
            gpt_defense = response_loop_gpt.choices[0].message.content
            status_updates.append({"model": "GPT", "content": gpt_defense, "step": f"라운드 {current_loop} 방어"})

            if "오류가 있었음을 인정합니다" in gpt_defense:
                points = (2**(2 * current_loop - 1)) - 1 # Gemini wins
                credit_scores["Gemini"] += points
                
                # Gemini wins, so the final answer is Gemini's proposed solution from the critique
                solution_parts = current_critique.split("## 올바른 해결책")
                if len(solution_parts) > 1:
                    final_answer = solution_parts[1].strip()
                else:
                    # Fallback if the marker is not found
                    final_answer = gpt_defense 

                winner = "Gemini"
                loop_active = False
                break

            response_loop_gemini = gemini_model.generate_content(
                [PROMPT_VERIFIER_REBUTTAL, f"GPT 방어:\n{gpt_defense}", pil_image_verify]
            )
            gemini_reaction = response_loop_gemini.text
            status_updates.append({"model": "Gemini", "content": gemini_reaction, "step": f"라운드 {current_loop} 재평가"})

            if "원래 주장이 옳았음을 인정합니다" in gemini_reaction:
                points = (2**(2 * current_loop)) - 1 # GPT wins
                credit_scores["GPT"] += points
                final_answer = gpt_defense
                winner = "GPT"
                loop_active = False
            elif "정확함을 확인했습니다" in gemini_reaction:
                points = (2**(2 * current_loop - 1)) - 1 # Gemini wins
                credit_scores["Gemini"] += points
                final_answer = gpt_defense
                winner = "Gemini"
                loop_active = False
            else:
                current_critique = gemini_reaction
                if current_loop == max_loops:
                    winner = "Draw (Timeout)"
                    score_gpt = credit_scores["GPT"]
                    score_gemini = credit_scores["Gemini"]
                    if score_gpt >= score_gemini:
                        final_answer = a01
                    else:
                        parts = current_critique.split("## 올바른 해결책")
                        if len(parts) > 1:
                            final_answer = parts[1].strip()
                        else:
                            final_answer = a01
                    loop_active = False
    
    save_project_scores(project_id, credit_scores)
    
    # 새로 추가된 5단계 요약 형식 생성
    # 참고: 더 깔끔한 요약 생성을 위해 소스 모델 접두사가 없는 원본 final_answer를 전달합니다.
    formatted_summary = format_final_summary(gemini_model, a01, r02, final_answer, winner, is_correct)

    # 프론트엔드에 반환되는 최종 답변은 새로 포맷된 요약문입니다.
    return {
        "winner": winner,
        "final_answer": formatted_summary, # 새로운 포맷의 요약문을 메인 답변으로 반환
        "scores": credit_scores,
        "process": status_updates
    }

# =======================================================
# [API 라우트] 웹 페이지 및 API 엔드포인트
# =======================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/solve', methods=['POST'])
def solve_problem():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
    image_file = request.files['image']
    user_question = request.form.get('question', 'Please solve the problem in the image.')
    project_id = request.form.get('project_id', PROJECT_ID) # PROJECT_ID는 폴백(fallback)으로 사용됩니다.

    if image_file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        result = run_analysis_logic(project_id, image_file, user_question)
        return jsonify(result)
    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({"error": "An unexpected error occurred."}), 500

@app.route('/api/scores/<project_id>', methods=['GET'])
def get_project_scores(project_id):
    scores = load_project_scores(project_id)
    return jsonify(scores)

# =======================================================
# [애플리케이션 실행]
# =======================================================
if __name__ == '__main__':
    app.run(debug=True, port=5000)

