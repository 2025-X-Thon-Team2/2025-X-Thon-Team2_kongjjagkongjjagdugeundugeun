import os
import json
import base64
from PIL import Image
from google import genai
from openai import OpenAI
import config

# =======================================================
# [Setup] Configuration
# =======================================================
PROJECT_ID = "team_hackathon_demo"
DB_FILE = "project_db.json"
IMAGE_FILENAME = "test_image.png"
USER_QUESTION = "이 이미지의 (2)번 문제를 풀고, 최종 정답을 도출해줘. 풀이과정을 상세히 서술해."

# =======================================================
# [Prompt Engineering] System Prompts (English)
# =======================================================

# 1. GPT (Solver) 초기 페르소나
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

# 2. Gemini (Verifier) 검증 페르소나
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

# 3. GPT (Solver) 방어/수정 페르소나
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

# 4. Gemini (Verifier) 재검증 페르소나
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

credit_scores = load_project_scores(PROJECT_ID)

def add_score(winner, points):
    global credit_scores
    if points > 0:
        credit_scores[winner] += points
        print(f"\n🎉 [Score Update] {winner} gets +{points} points! (Total: {credit_scores})")
        save_project_scores(PROJECT_ID, credit_scores)
    else:
        print(f"\n😐 [No Score] Consensus reached immediately. (Total: {credit_scores})")

def get_score_by_depth(loop_count, winner_role):
    # Mersenne Number Rule: 1, 3, 7, 15...
    if winner_role == "Gemini": return (2 ** (loop_count * 2 - 1)) - 1
    else: return (2 ** (loop_count * 2)) - 1

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# =======================================================
# [Main Execution]
# =======================================================
clientGemini = genai.Client(api_key=config.GOOGLE_API_KEY)
clientGPT = OpenAI(api_key=config.OPENAI_API_KEY)

if not os.path.exists(IMAGE_FILENAME):
    print(f"❌ Error: '{IMAGE_FILENAME}' not found.")
    exit()

print(f"🚀 [GemPT] High-Stakes Verification System Started")
print(f"📊 Current Credit Scores: {credit_scores}\n")

# -------------------------------------------------------
# [Step 1] GPT Initial Solution
# -------------------------------------------------------
print("[1] Model 01 (GPT) is Solving...", end="", flush=True)
base64_image = encode_image_to_base64(IMAGE_FILENAME)
response_01 = clientGPT.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": PROMPT_SOLVER_INIT},
        {"role": "user", "content": [
            {"type": "text", "text": USER_QUESTION},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]}
    ]
)
A01 = response_01.choices[0].message.content
print(" Done.")
# print(f"\n[GPT Answer Preview]: {A01[:100]}...\n") 

# -------------------------------------------------------
# [Step 2] Gemini Verification
# -------------------------------------------------------
print("[2] Model 02 (Gemini) is Auditing...", end="", flush=True)
pil_image = Image.open(IMAGE_FILENAME)
response_02 = clientGemini.models.generate_content(
    model="gemini-2.0-flash",
    contents=[PROMPT_VERIFIER_INIT, f"User Question: {USER_QUESTION}\n\nModel 01 Solution:\n{A01}", pil_image]
)
R02 = response_02.text
print(" Done.")

# 판정 로직 파싱
is_correct = "VERDICT: CORRECT" in R02

# -------------------------------------------------------
# [Step 3] Conflict Resolution Loop
# -------------------------------------------------------
final_answer = ""
winner = ""

if is_correct:
    print("✅ Verdict: CORRECT (Consensus Reached)")
    add_score("None", 0)
    final_answer = A01
    winner = "Draw (Agreement)"
else:
    print("\n🚨 Verdict: INCORRECT -> Entering Debate Loop...")
    current_loop = 0
    MAX_LOOPS = 3
    loop_active = True
    
    # Gemini의 비평 내용 추출 (VERDICT: INCORRECT 뒷부분)
    current_critique = R02.replace("VERDICT: INCORRECT", "").strip()

    while loop_active and current_loop < MAX_LOOPS:
        current_loop += 1
        print(f"\n--- [Round {current_loop}] ---")

        # 3-1. GPT Defense
        print("🤖 GPT is responding to critique...", end="", flush=True)
        response_loop_gpt = clientGPT.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": PROMPT_SOLVER_DEFENSE},
                {"role": "user", "content": f"Auditor's Critique:\n{current_critique}"}
            ]
        )
        gpt_defense = response_loop_gpt.choices[0].message.content
        print(" Done.")
        print(f"   👉 GPT Strategy: {'ADMIT' if 'ADMIT' in gpt_defense else 'REBUT'}")

        # GPT가 패배를 인정한 경우
        if "[DECISION]: ADMIT" in gpt_defense:
            points = get_score_by_depth(current_loop, "Gemini")
            add_score("Gemini", points)
            
            # Gemini의 Critique에 있던 정답이나, GPT가 수정한 답을 채택
            # (여기서는 수정된 GPT 답을 채택)
            final_answer = gpt_defense.replace("[DECISION]: ADMIT", "").strip()
            winner = "Gemini"
            loop_active = False
            break

        # 3-2. Gemini Re-evaluation
        print("✨ Gemini is reviewing the defense...", end="", flush=True)
        response_loop_gemini = clientGemini.models.generate_content(
            model="gemini-2.0-flash",
            contents=[PROMPT_VERIFIER_REBUTTAL, f"GPT Defense:\n{gpt_defense}", pil_image]
        )
        gemini_reaction = response_loop_gemini.text
        print(" Done.")
        print(f"   👉 Gemini Verdict: {gemini_reaction.splitlines()[0]}")

        if "VERDICT: CONCEDED" in gemini_reaction:
            # Gemini가 GPT의 반박에 설득됨 (GPT 승리)
            points = get_score_by_depth(current_loop, "GPT")
            add_score("GPT", points)
            final_answer = gpt_defense.replace("[DECISION]: REBUT", "").strip()
            winner = "GPT"
            loop_active = False
        
        elif "VERDICT: RESOLVED" in gemini_reaction:
            # GPT가 인정했고 Gemini가 확인 (Gemini 승리 - 위에서 break 안 걸렸을 경우 대비)
            points = get_score_by_depth(current_loop, "Gemini")
            add_score("Gemini", points)
            final_answer = gpt_defense
            winner = "Gemini"
            loop_active = False

        else:
            # VERDICT: REJECTED (계속 싸움)
            current_critique = gemini_reaction # 비평 업데이트
            
            # 최대 루프 도달 시 누적 신뢰도 판정
            if current_loop == MAX_LOOPS:
                print("\n🛑 Max loops reached! Using Credit Scores to decide.")
                score_gpt = credit_scores["GPT"]
                score_gemini = credit_scores["Gemini"]
                
                if score_gpt >= score_gemini:
                    winner = f"GPT (Credit Win: {score_gpt} vs {score_gemini})"
                    final_answer = A01 # 신뢰도 높은 초기 답변 채택
                else:
                    winner = f"Gemini (Credit Win: {score_gemini} vs {score_gpt})"
                    final_answer = current_critique # Gemini의 마지막 비평 내의 정답 추출 시도 (구현 편의상 전체 텍스트)
                loop_active = False

# =======================================================
# [Final Report]
# =======================================================
print("\n" + "="*60)
print(f"📢 [GemPT] Final Consensus Report")
print("="*60)
print(f"📊 [Credit Scores]")
print(f"   🔹 ChatGPT : {credit_scores['GPT']}")
print(f"   🔸 Gemini  : {credit_scores['Gemini']}")
print(f"\n🏆 [Winner]: {winner}")
print("-" * 60)
print(f"📝 [Final Solution]")
print(final_answer)
print("="*60)
