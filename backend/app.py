import os
import json
import base64
from flask import Flask, request, jsonify, render_template, send_from_directory
from PIL import Image
import google.generativeai as genai
from openai import OpenAI

# =======================================================
# Flask App Initialization
# =======================================================
app = Flask(__name__, template_folder='../frontend', static_folder='../frontend/static')

# =======================================================
# [Setup] Configuration
# =======================================================
# 환경 변수에서 API 키를 불러오는 것이 가장 안전합니다.
# os.environ.get()을 사용하면 키가 없을 때 None을 반환하여 오류를 방지할 수 있습니다.
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "YOUR_GOOGLE_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")

PROJECT_ID = "team_hackathon_demo"
DB_FILE = "project_db.json"

# =======================================================
# [Prompt Engineering] System Prompts
# =======================================================
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
PROMPT_VERIFIER_REBUTTAL = """
The Solver has responded to your critique.
If they admitted the error, confirm it. If they rebutted, evaluate their defense.
**Output Rules:**
- If they admitted and fixed it correctly, say: "VERDICT: RESOLVED (Winner: Gemini)"
- If they defended and convinced you, say: "VERDICT: CONCEDED (Winner: GPT)"
- If they are still wrong, say: "VERDICT: REJECTED" and state the final correct answer again.
"""

# =======================================================
# [Functions] DB & Utils
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

# =======================================================
# [Core Logic]
# =======================================================
def run_analysis_logic(image_file, user_question):
    # API 키 설정
    genai.configure(api_key=GOOGLE_API_KEY)
    
    # Initialize clients
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
    client_gpt = OpenAI(api_key=OPENAI_API_KEY)
    
    credit_scores = load_project_scores(PROJECT_ID)

    # 1. GPT Initial Solution
    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    response_01 = client_gpt.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": PROMPT_SOLVER_INIT},
            {"role": "user", "content": [
                {"type": "text", "text": user_question},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]}
        ]
    )
    a01 = response_01.choices[0].message.content

    # 2. Gemini Verification
    image_file.seek(0) # Reset file pointer for PIL
    pil_image = Image.open(image_file)
    response_02 = gemini_model.generate_content(
        [PROMPT_VERIFIER_INIT, f"User Question: {user_question}\n\nModel 01 Solution:\n{a01}", pil_image]
    )
    r02 = response_02.text
    
    is_correct = "VERDICT: CORRECT" in r02
    
    # 3. Conflict Resolution Loop
    final_answer = ""
    winner = ""
    status_updates = []
    status_updates.append({"model": "GPT", "content": a01, "step": "Initial Solution"})
    status_updates.append({"model": "Gemini", "content": r02, "step": "Verification"})

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
# [API Routes]
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
        # 프로덕션에서는 보다 상세한 로깅과 일반적인 에러 메시지를 사용해야 합니다.
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # 디버그 모드는 개발 중에만 사용해야 합니다.
    app.run(debug=True, port=5000)
