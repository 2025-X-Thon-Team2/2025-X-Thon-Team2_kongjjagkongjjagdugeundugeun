GemPT API 명세서 (API Specification)

1. 프로젝트명
   GemPT: AI 기반 교차 검증 시스템

2. 배경
   본 문서는 GemPT 시스템의 백엔드 API 엔드포인트를 설명합니다. 이 API는 AI 기반 문제 해결, 교차 검증, 그리고 AI 모델 간의 토론 과정을 지원합니다.

3. 기본 URL (개발 환경)
   http://127.0.0.1:5000

4. 인증
   현재 API 호출을 위한 별도의 인증 메커니즘은 구현되어 있지 않습니다. (API 키는 서버 측에서 관리됩니다.)

---

5. API 엔드포인트 상세

   5.1. 프론트엔드 HTML 페이지 제공

      5.1.1. 엔드포인트
            /

      5.1.2. 메서드
            GET

      5.1.3. 설명
            웹 애플리케이션의 메인 프론트엔드 HTML 페이지를 제공합니다. 사용자가 브라우저를 통해 애플리케이션에 접속할 때 사용됩니다.

      5.1.4. 요청 파라미터
            없음

      5.1.5. 응답
            Content-Type: text/html
            바디: frontend/index.html 파일의 HTML 내용

   5.2. 문제 제출 및 AI 솔루션 요청

      5.2.1. 엔드포인트
            /api/solve

      5.2.2. 메서드
            POST

      5.2.3. 설명
            사용자가 문제 이미지와 질문을 제출하면, AI 시스템이 다음 과정을 거쳐 최종 솔루션과 함께 업데이트된 신뢰도 점수를 반환합니다:
            1) 이미지 과목 인식 및 사전 정보 크롤링
            2) 다국어 번역 AI 로직 처리
            3) GPT와 Gemini 간의 문제 해결, 검증 및 토론
            이 모든 과정은 제출된 project_id에 따라 기록되고 점수에 반영됩니다.

      5.2.4. 요청 바디 (Form Data - multipart/form-data)
            image: File (필수) - 문제 내용을 담은 이미지 파일.
            question: String (선택 사항) - 문제에 대한 사용자의 질문 또는 프롬프트. 제공되지 않을 경우 기본값은 'Please solve the problem in the image.' 입니다.
            project_id: String (선택 사항) - 문제가 속한 프로젝트의 고유 ID. 신뢰도 점수 영속성 관리에 사용됩니다. 제공되지 않을 경우 기본값은 백엔드에 정의된 PROJECT_ID (예: "team_hackathon_demo")입니다.

      5.2.5. 응답 바디 (JSON)
            winner: String - 토론에서 승리한 AI ("GPT", "Gemini"), 합의된 경우 ("Draw (Agreement)"), 또는 제한 시간을 초과한 경우 ("Draw (Timeout)")를 나타냅니다.
            final_answer: String - AI 시스템이 검증을 거쳐 제공하는 최종 해결책. LaTeX 형식의 수학 표현식이 포함될 수 있습니다.
            scores: Object - 해당 프로젝트에 대한 GPT 및 Gemini의 현재 신뢰도 점수.
              GPT: Integer - GPT의 현재 신뢰도 점수.
              Gemini: Integer - Gemini의 현재 신뢰도 점수.
            process: Array of Objects - AI 토론 과정의 상세 로그 배열.
              model: String - 메시지를 생성한 AI 또는 시스템 ("GPT", "Gemini", "System").
              content: String - AI의 메시지 내용 또는 시스템 업데이트 메시지.
              step: String - 해당 과정의 단계 설명 (예: "주제 분류", "초기 해결책", "검증", "라운드 1 방어").

      5.2.6. 에러 응답
            400 Bad Request: {"error": "No image file provided"} 또는 {"error": "No selected file"}
            500 Internal Server Error: {"error": "An unexpected error occurred."}

   5.3. 프로젝트별 신뢰도 점수 조회

      5.3.1. 엔드포인트
            /api/scores/<project_id>

      5.3.2. 메서드
            GET

      5.3.3. 설명
            지정된 project_id에 해당하는 프로젝트의 현재 GPT 및 Gemini 신뢰도 점수를 조회합니다.

      5.3.4. URL 파라미터
            <project_id>: String (필수) - 점수를 조회할 프로젝트의 고유 식별자.

      5.3.5. 응답 바디 (JSON)
            GPT: Integer - 해당 프로젝트에 대한 GPT의 현재 신뢰도 점수.
            Gemini: Integer - Gemini의 현재 신뢰도 점수.

      5.3.6. 특이사항
            project_id에 해당하는 점수가 project_db.json 파일에 없을 경우, 기본값인 {"GPT": 0, "Gemini": 0}을 반환합니다. 이는 오류로 처리되지 않습니다.

---

6. API 상세 흐름도

   본 섹션은 /api/solve 엔드포인트 호출 시 발생하는 AI 시스템의 상세 처리 흐름을 설명합니다.
```mermaid
graph TD

    %% =========================
    %% 프론트엔드 영역 (FE)
    %% =========================
    subgraph FE [프론트엔드]
        A[User Input: Question, Image] --> B[POST /api/solve Request]
    end

    %% =========================
    %% 백엔드 영역 (BE)
    %% =========================
    subgraph BE [백엔드]
        B --> C{run_analysis_logic 함수 시작}

        C --> D[1. 프로젝트별 신뢰도 점수 로드]
        D --> E[2. 이미지 과목 분류 (Gemini)]
        E --> F[3. 지식 크롤링 & 패키지 생성 (Gemini, SerpAPI)]
        F --> G[4. 다국어 번역 AI 로직]
        G --> H[5. GPT 초기 해결책 생성 (A01)]
        H --> I[6. Gemini 검증 (R02)]

        I --> J{R02 == "정답"?}

        %% ----- Gemini가 GPT 답변에 동의하는 경우 -----
        J -- Yes --> K[신뢰도 업데이트: 동의 (Draw Agreement)]
        K --> L[최종 답변 = A01]
        L --> M[토론 루프 종료]

        %% ----- Gemini가 GPT 답변에 반박하는 경우 -----
        J -- No --> N[토론 루프 시작 (max_loops = 5)]
        N --> O[Loop++ & GPT 방어 (gpt_defense)]

        O --> P{GPT 오류 인정?}

        %% GPT가 틀렸다고 인정 → Gemini 승리
        P -- Yes --> Q[신뢰도 업데이트: Gemini 승리]
        Q --> R[최종 답변 = Gemini 수정 제안]
        Q --> M
        R --> M

        %% GPT가 인정하지 않음 → Gemini 재평가
        P -- No --> S[Gemini 재평가 (gemini_reaction)]
        S --> T{Gemini convinced / confirmed?}

        %% Gemini가 GPT의 반박에 설득됨 → GPT 승리
        T -- Yes (conv.) --> U[신뢰도 업데이트: GPT 승리]
        U --> V[최종 답변 = GPT 방어]
        U --> M
        V --> M

        %% Gemini가 GPT 방어를 사실상 정정(correction)한 경우 → Gemini 승리
        T -- Yes (corr.) --> W[신뢰도 업데이트: Gemini 승리]
        W --> X[최종 답변 = GPT 방어]
        W --> M
        X --> M

        %% 둘 다 계속 우기면 → 반복/타임아웃 판정
        T -- No --> Y{Loop < max_loops?}
        Y -- Yes --> O
        Y -- No --> Z[신뢰도 업데이트: Draw (Timeout)]
        Z --> AA[신뢰도 비교 후 최종 답변 결정]
        AA --> M

        %% ----- 백엔드 종료 처리 -----
        M --> BB[7. 프로젝트별 신뢰도 점수 저장]
        BB --> CC[8. 최종 요약 및 백엔드 응응 생성]
        CC --> DD[백엔드 (BE) - run_analysis_logic 종료]
    end

    %% =========================
    %% 백 → 프론트 결과 전달
    %% =========================
    DD --> EE[프론트엔드 (FE): 최종 답변 및 토론 과정, 점수 표시]
```

   [프론트엔드 (FE)]
   User Question & Image 입력
     |
     v
   [FE] POST /api/solve (project_id, question, image 전송)
     |
     v
   [백엔드 (BE) - run_analysis_logic 시작]
   1. 프로젝트별 신뢰도 점수 로드 (load_project_scores(project_id))
   2. 이미지 전처리 & 과목 분류 (Gemini - PROMPT_SUBJECT_CLASSIFIER)
      - 결과: Subject
     |
     v
   3. 지식 크롤링 & 패키지 생성 (Gemini)
      - Subject 기반 검색어 생성 (PROMPT_KNOWLEDGE_CRAWLER_QUERIES)
      - Google Search API (SerpAPI)로 검색 수행
      - 검색 결과로 지식 패키지 생성 (PROMPT_KNOWLEDGE_PACKAGE_GENERATOR)
      - 결과: knowledge_package_str
     |
     v
   4. 다국어 번역 AI 로직 (Implicit/Optional - 사용자 질문 번역, 검색 결과 번역 등)
      (이전 논의된 '한국어 질문 -> 영어 번역 -> 영어 검색/답변 생성 -> 한국어 번역' 로직)
     |
     v
   5. GPT 초기 해결책 생성 (GPT-4o - PROMPT_SOLVER_INIT)
      - knowledge_package_str & Image & Question 전달
      - 결과: A01 (GPT의 초기 답변)
     |
     v
   6. Gemini 검증 (Gemini - PROMPT_VERIFIER_INIT)
      - Q + A01 + Image 전달 (GPT의 답변에 대한 검증)
      - 결과: R02 (Gemini의 평가: "정답" 또는 "오류 + 근거")
     |
     v
   [토론 루프 시작]
   Loop = 0, max_loops = 5

   IF R02 == "정답"
     |
     v
     신뢰도 업데이트: GPT와 Gemini 동의 (Draw Agreement)
     신뢰도 점수 변경 없음 (또는 미미한 기본 점수 부여)
     최종 답변 = A01
     탈출
     |
     v
   ELSE (R02 == "오류")
     |
     v
     Loop += 1
     [GPT 방어] GPT에 Gemini의 비판 전달 (GPT-4o - PROMPT_SOLVER_DEFENSE)
       - 결과: GPT의 방어 (gpt_defense)
       |
       v
     IF GPT admits error ("오류가 있었음을 인정합니다")
       |
       v
       신뢰도 업데이트: Gemini 승리
       Gemini 점수 증가 (points = (2**(2 * Loop - 1)) - 1)
       최종 답변 = Gemini의 수정된 해결책 (R02에서 추출) 또는 GPT의 수정된 답변
       탈출
       |
       v
     ELSE (GPT defends)
       |
       v
       [Gemini 재평가] Gemini에 GPT의 방어 전달 (Gemini - PROMPT_VERIFIER_REBUTTAL)
         - 결과: Gemini의 반응 (gemini_reaction)
         |
         v
       IF Gemini is convinced by GPT's defense ("원래 주장이 옳았음을 인정합니다")
         |
         v
         신뢰도 업데이트: GPT 승리
         GPT 점수 증가 (points = (2**(2 * Loop)) - 1)
         최종 답변 = GPT의 방어 (gpt_defense)
         탈출
         |
         v
       ELSE IF Gemini confirms correction ("정확함을 확인했습니다")
         |
         v
         신뢰도 업데이트: Gemini 승리
         Gemini 점수 증가 (points = (2**(2 * Loop - 1)) - 1)
         최종 답변 = GPT의 방어 (gpt_defense)
         탈출
         |
         v
       ELSE (Gemini still finds error or rejects defense)
         |
         v
         IF Loop < max_loops (5회)
           |
           v
           Gemini의 새로운 비판으로 다음 루프 진행
           (current_critique = gemini_reaction)
           재반복
           |
           v
         ELSE (Loop == max_loops, 토론 종료)
           |
           v
           신뢰도 업데이트: Draw (Timeout)
           신뢰도 비교 (GPT score vs Gemini score)
           승자 모델에 따라 최종 답변 결정
           탈출
           |
           v
   [토론 루프 종료]
     |
     v
   7. 프로젝트별 신뢰도 점수 저장 (save_project_scores(project_id, credit_scores))
   8. 최종 요약 형식 생성 (format_final_summary)
   9. 백엔드 응답 (winner, final_answer, scores, process 로그 포함)

   [백엔드 (BE) - run_analysis_logic 종료]
     |
     v
   [프론트엔드 (FE)]
   사용자에게 최종 답변 및 토론 과정, 점수 표시

---

7. 신뢰도 점수 산정 방식

   Gemini와 GPT의 신뢰도 점수는 토론 루프(Loop)의 결과에 따라 동적으로 산정됩니다. 'Loop'는 토론 라운드를 의미하며, 값이 1부터 시작합니다.

   *   Gemini 승리 (GPT가 오류를 인정하거나 Gemini의 수정에 동의):
       Gemini 점수 증가량 = (2^(2 * Loop - 1)) - 1
       (예: Loop=1일 때 (2^1)-1 = 1점, Loop=2일 때 (2^3)-1 = 7점)

   *   GPT 승리 (Gemini가 GPT의 반박에 설득):
       GPT 점수 증가량 = (2^(2 * Loop)) - 1
       (예: Loop=1일 때 (2^2)-1 = 3점, Loop=2일 때 (2^4)-1 = 15점)

   이러한 방식으로 토론 루프가 길어질수록 승리 모델이 얻는 점수가 기하급수적으로 증가하여, 더 빠르고 정확한 합의 도출을 장려합니다.
