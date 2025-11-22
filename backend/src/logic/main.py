import os
import json
import base64
from PIL import Image
from google import genai
from openai import OpenAI
import config

# =======================================================
# [설정] 파일명 및 질문
# =======================================================
IMAGE_FILENAME = "test_image.png" 
USER_QUESTION = "이 이미지의 (1) 문제를 풀고, 최종 정답을 도출해줘. 풀이과정 서술해 "

# =======================================================
# [설정] 신용도 점수 관리
# =======================================================
credit_scores = {"GPT": 0, "Gemini": 0}

def add_score(winner, points):
    if points > 0:
        credit_scores[winner] += points
        print(f"\n🎉 [점수 획득] {winner}에게 {points}점 부여! (현재: {credit_scores})")
    else:
        print(f"\n😐 [점수 없음] 합의에 도달했으나 점수 변동 없음. (현재: {credit_scores})")

def get_score_by_depth(loop_count, winner_role):
    # Mersenne Number 규칙: 1, 3, 7, 15...
    if winner_role == "Gemini": 
        return (2 ** (loop_count * 2 - 1)) - 1
    else: 
        return (2 ** (loop_count * 2)) - 1

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# =======================================================
# [메인] 실행 로직
# =======================================================
clientGemini = genai.Client(api_key=config.GOOGLE_API_KEY)
clientGPT = OpenAI(api_key=config.OPENAI_API_KEY)

if not os.path.exists(IMAGE_FILENAME):
    print(f"❌ 오류: '{IMAGE_FILENAME}' 없음")
    exit()

print(f"🚀 [GemPT] 신용도 경쟁 시스템 가동 (초기점수: {credit_scores})")

# [Step 1] GPT - 초기 답변
print("\n[1] ChatGPT 분석 중...", end="", flush=True)
base64_image = encode_image_to_base64(IMAGE_FILENAME)
response_01 = clientGPT.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "당신은 전문가입니다. 정답을 도출하세요."},
        {"role": "user", "content": [
            {"type": "text", "text": USER_QUESTION},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]}
    ]
)
A01 = response_01.choices[0].message.content
print(" 완료!")

# [Step 2] Gemini - 검증 (프롬프트 수정됨!)
print("[2] Gemini 검증 중...", end="", flush=True)
pil_image = Image.open(IMAGE_FILENAME)

# 🔥 여기가 핵심 수정 부분입니다 🔥
verify_prompt = f"""
Q: {USER_QUESTION}
A01: {A01}

[검증 가이드]
1. 답변이 완벽하게 정답이면 "A01 정답"이라고만 출력하세요.
2. 틀렸거나 부족하다면 "A01 오답"이라고 첫 줄에 적고, 다음 내용을 반드시 포함하세요:
   - **[오답 이유]**: 왜 틀렸는지 논리적 근거
   - **[올바른 정답과 풀이]**: 당신이 생각하는 정확한 정답과 상세한 풀이 과정
"""

response_02 = clientGemini.models.generate_content(
    model="gemini-2.5-pro",
    contents=[verify_prompt, pil_image]
)
R02 = response_02.text
eval_result = "correct" if "A01 정답" in R02 else "incorrect"
print(f" 완료! (판정: {eval_result})")

# [Step 3] 점수 판정 및 루프
final_answer = ""
winner = ""

if eval_result == "correct":
    add_score("None", 0) 
    final_answer = A01
    winner = "Draw (Agreement)"
else:
    print("\n⚔️ 의견 충돌! 교차 검증 루프 진입...")
    current_loop = 0
    MAX_LOOPS = 3 
    loop_active = True
    
    current_rebuttal = R02.replace("A01 오답", "").strip()

    while loop_active and current_loop < MAX_LOOPS:
        current_loop += 1
        print(f"\n--- [Round {current_loop}] ---")

        # 3-1. GPT의 방어
        response_loop_gpt = clientGPT.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "지적을 인정하면 '인정합니다', 아니면 '반박합니다'와 이유를 대세요."},
                {"role": "user", "content": f"상대 지적 및 정답 제시: {current_rebuttal}"}
            ]
        )
        gpt_defense = response_loop_gpt.choices[0].message.content
        print(f"🤖 GPT 반응: {gpt_defense[:50]}...")

        if "인정합니다" in gpt_defense:
            points = get_score_by_depth(current_loop, "Gemini")
            add_score("Gemini", points)
            
            # Gemini가 제시했던 [올바른 정답과 풀이]를 최종 답변으로 채택
            final_answer = current_rebuttal 
            winner = "Gemini"
            loop_active = False
            break

        # 3-2. GPT 반박 시 Gemini 재검증
        # 여기도 정답을 다시 요구하도록 프롬프트 강화
        response_loop_gemini = clientGemini.models.generate_content(
            model="gemini-2.5-pro",
            contents=[f"GPT 반박: {gpt_defense}\n이 반박이 맞으면 'GPT 인정', 틀렸으면 '재반박'과 함께 **확실한 정답**을 다시 설명하세요.", pil_image]
        )
        gemini_reaction = response_loop_gemini.text
        print(f"✨ Gemini 재반응: {gemini_reaction[:50]}...")

        if "GPT 인정" in gemini_reaction:
            points = get_score_by_depth(current_loop, "GPT")
            add_score("GPT", points)
            final_answer = gpt_defense 
            winner = "GPT"
            loop_active = False
        else:
            current_rebuttal = gemini_reaction
            if current_loop == MAX_LOOPS:
                print("\n🛑 최대 루프 초과!")
                if credit_scores["GPT"] >= credit_scores["Gemini"]:
                    winner = "GPT (신용도 우위)"
                    final_answer = A01
                else:
                    winner = "Gemini (신용도 우위)"
                    final_answer = current_rebuttal

# =======================================================
# [최종 리포트]
# =======================================================
print("\n" + "="*60)
print(f"📢 [GemPT] 최종 결과 리포트")
print("="*60)
print(f"📊 [현재 신용도 점수]")
print(f"   🔹 ChatGPT : {credit_scores['GPT']}점")
print(f"   🔸 Gemini  : {credit_scores['Gemini']}점")
print(f"\n🏆 [이번 토론 승자]: {winner}")
print("-" * 60)
print(f"📝 [최종 답변 (승자의 솔루션)]")
# 답변이 너무 길어지는 것을 방지하거나, 포맷팅을 위해 줄바꿈 추가
print(final_answer)
print("="*60)