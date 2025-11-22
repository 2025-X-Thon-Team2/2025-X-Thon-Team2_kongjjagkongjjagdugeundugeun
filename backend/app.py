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
SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY", "YOUR_SERPAPI_API_KEY") # SerpApi 키 추가

PROJECT_ID = "team_hackathon_demo"
DB_FILE = "project_db.json"

# =======================================================
# [Prompt Engineering] System Prompts
# =======================================================
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

PROMPT_SEARCH_QUERY_GENERATOR = """
Based on the pre-analysis of the user's request, generate 1-2 concise Google search queries to find relevant formulas, definitions, or context.
**Pre-analysis Report:**
---
{pre_analysis_result}
---
**Instructions:**
- Focus on the core concepts, symbols, or theorems identified in the report.
- Output ONLY the search queries, one per line. Do not add any other text.
**Example:**
- **Input:** Subject: Calculus, Goal: Find the derivative of f(x) = x^3.
- **Output:**
  derivative of a cubic function
  power rule for differentiation
"""

PROMPT_SOLVER_INIT = """
You are a Distinguished Professor of Mathematics and Logic. Your goal is to provide a flawless, step-by-step solution in **English**.
**1. Pre-analysis from a colleague:**
---
{pre_analysis_result}
---
**2. Relevant information from a web search:**
---
{search_context}
---
**Instructions:**
1.  Use the pre-analysis and, most importantly, the web search results to formulate your solution.
2.  Provide a clear, step-by-step reasoning for your solution.
3.  **You MUST cite a credible source** for the primary theorem, formula, or method used. This can be from the web search or your own knowledge.
4.  Conclude with a definitive final answer.
**Output Format (Strictly follow):**
## Step-by-Step Solution
(Your detailed solution here)

### Source
- **Method/Theorem:** [e.g., Pythagorean theorem]
- **Citation:** [Provide a URL or reference to the source]

### Final Answer
[Your Result Here]
"""

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

PROMPT_SOLVER_DEFENSE = """
You are in a high-stakes debate. The 'Chief Auditor' (Gemini) has criticized your previous solution. Your response must be in **English**.
**Your Task:**
1.  Review the Auditor's critique carefully.
2.  **Self-Correction:** If the critic is right, admit it. Start with `[DECISION]: ADMIT`, then provide the fully corrected solution, including a new or corrected source.
3.  **Defense:** If you are certain the critic is wrong, defend your stance. Start with `[DECISION]: REBUT` and explain why your original logic and source are correct.
"""

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

def get_score_by_depth(loop_count, winner_role):
    if winner_role == "Gemini": return (2 ** (loop_count * 2 - 1)) - 1
    else: return (2 ** (loop_count * 2)) - 1

def perform_google_search(query):
    try:
        search = GoogleSearch({"q": query, "api_key": SERPAPI_API_KEY})
        results = search.get_dict()
        
        snippets = []
        if "organic_results" in results:
            for result in results["organic_results"][:3]:
                snippet = result.get("snippet", "No snippet available.")
                link = result.get("link", "#")
                snippets.append(f"- Title: {result.get('title', 'N/A')}\n  Snippet: {snippet}\n  Source: {link}")
        
        return "\n".join(snippets) if snippets else "No relevant search results found."
    except Exception as e:
        print(f"Error during Google Search: {e}")
        return "Error performing search."

# =======================================================
# [Core Logic] AI Analysis and Debate Process
# =======================================================
def run_analysis_logic(image_file, user_question):
    genai.configure(api_key=GOOGLE_API_KEY)
    client_gpt = OpenAI(api_key=OPENAI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-2.5-pro')
    
    credit_scores = load_project_scores(PROJECT_ID)
    status_updates = []

    # === Step 0: Gemini Pre-analysis ===
    image_file.seek(0)
    pil_image = Image.open(image_file)
    pre_analysis_response = gemini_model.generate_content(
        [PROMPT_PRE_ANALYZER, user_question, pil_image]
    )
    pre_analysis_result = pre_analysis_response.text
    status_updates.append({"model": "Gemini", "content": pre_analysis_result, "step": "Pre-analysis"})

    # === Step 0.5 (New): Google Search ===
    search_query_prompt = PROMPT_SEARCH_QUERY_GENERATOR.format(pre_analysis_result=pre_analysis_result)
    search_query_response = gemini_model.generate_content([search_query_prompt])
    search_queries = search_query_response.text.strip().split('\n')
    
    googling_content = "Generated Search Queries:\n" + "\n".join(search_queries) + "\n\n"
    
    all_search_results = []
    for query in search_queries:
        if query:
            results = perform_google_search(query)
            all_search_results.append(f"Search results for '{query}':\n{results}")
    
    search_context = "\n\n".join(all_search_results)
    googling_content += search_context
    status_updates.append({"model": "System", "content": googling_content, "step": "Googling"})

    # === Step 1: GPT Initial Solution ===
    image_file.seek(0)
    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    solver_prompt = PROMPT_SOLVER_INIT.format(
        pre_analysis_result=pre_analysis_result,
        search_context=search_context
    )
    
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
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/solve', methods=['POST'])
def solve_problem():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
    image_file = request.files['image']
    user_question = request.form.get('question', 'Please solve the problem in the image.')

    if image_file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        result = run_analysis_logic(image_file, user_question)
        return jsonify(result)
    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({"error": "An unexpected error occurred."}), 500

# =======================================================
# [애플리케이션 실행]
# =======================================================
if __name__ == '__main__':
    app.run(debug=True, port=5000)

