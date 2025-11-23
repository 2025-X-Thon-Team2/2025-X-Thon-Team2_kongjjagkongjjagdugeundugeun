# GemPT: AI 기반 교차 검증 시스템

AI 모델 간 지능형 토론을 통해 문제 해결의 신뢰도를 극대화하는 웹 애플리케이션

## 1. 프로젝트 개요

GemPT는 AI 시대에 정보의 홍수 속에서 AI 답변의 신뢰성 부족이라는 핵심 문제에 주목했습니다. 청년들이 학습 및 경력 개발 과정에서 복잡한 문제를 해결할 때, 단순히 AI의 답변에 의존하는 것을 넘어 그 답변이 얼마나 정확하고 신뢰할 수 있는지 검증하는 것이 필수적입니다.

저희 GemPT는 이러한 문제를 해결하기 위해 OpenAI의 GPT 모델을 '문제 해결사(Solver)'로, Google의 Gemini 모델을 '검증자(Verifier)'로 활용하는 **혁신적인 듀얼 AI 토론 시스템**을 구축했습니다. AI 스스로 자신의 답변을 검증하고, 나아가 서로 토론하여 최종 답변의 정확도를 높이는 방식입니다.

특히, 청년 취업 및 경력 성장을 지원하는 플랫폼으로서, GemPT는 다음과 같은 가치를 제공합니다:
*   **신뢰성 높은 지식 제공:** 검증된 AI 답변을 통해 잘못된 정보 습득을 방지하고 효과적인 학습을 지원합니다.
*   **문제 해결 능력 향상:** AI의 투명한 토론 과정을 통해 사용자가 문제 해결의 논리적 흐름을 이해하고 학습하는 데 기여합니다.
*   **기술적 한계 극복:** AI의 이미지 인식 및 언어적 한계를 극복하기 위한 다양한 로직을 통합하여 최적의 솔루션을 제공합니다.

## 2. 주요 기능

*   **이미지 기반 문제 제출 및 AI 해결:**
    *   수학 문제, 다이어그램 등 이미지 형태의 문제를 업로드하여 AI에 질문합니다.
    *   AI가 이미지 내용을 분석하고 문제 해결을 시도합니다.
*   **듀얼 AI (GPT & Gemini) 교차 검증 및 토론 루프:**
    *   GPT가 제시한 초기 해결책을 Gemini가 '감사관'으로서 엄격하게 검증합니다.
    *   오류 발견 시, GPT와 Gemini는 최대 5라운드까지 '토론'을 진행하며 상호 비판 및 자기 수정을 통해 최종 답변의 정확도를 높입니다.
*   **AI 신뢰도 점수 시스템:**
    *   각 AI 모델의 토론 과정에서의 성능(오류 인정, 성공적인 반박 등)에 따라 신뢰도 점수가 동적으로 부여됩니다.
    *   이 점수는 프로젝트별로 관리되며, AI들이 의견 불일치 상황에 놓일 때 어느 모델의 의견을 더 신뢰해야 할지 판단하는 중요한 지표로 활용됩니다.
*   **이미지 과목 인식 및 사전 정보 크롤링:**
    *   제출된 문제 이미지의 과목(예: 공학 선형대수학)을 AI가 먼저 인식합니다.
    *   인식된 과목을 기반으로 Google Search API (SerpAPI)를 활용하여 문제 해결에 필요한 사전 정보(수식, 기호, 기본 정리 등)를 자동으로 크롤링하여 GPT에게 제공함으로써, AI의 답변 정확도를 비약적으로 향상시킵니다.
*   **다국어 번역 AI 로직:**
    *   사용자의 한국어 질문을 영어로 번역하여 AI에게 전달하고, 영어 기반의 지식 검색 및 답변 생성을 수행합니다.
    *   생성된 답변을 최종적으로 한국어로 다시 번역하여 사용자에게 제공함으로써, AI 모델의 언어적 강점(영어가 더 정확한 답변을 낼 때가 많음)을 활용하여 최적의 답변을 도출합니다.
*   **LaTeX 수식 자동 렌더링:**
    *   AI가 생성한 LaTeX 형식의 수학 수식을 웹 환경에서 자동으로 인식하고 MathJax 라이브러리를 통해 시각적으로 아름답고 명확하게 렌더링하여 사용자 편의성을 극대화합니다.
*   **상세 토론 과정 로그 제공:**
    *   AI들이 문제를 해결하고 검증하며 토론하는 모든 과정을 상세한 로그로 기록하여 사용자에게 투명하게 공개하고, AI의 추론 과정을 이해할 수 있도록 돕습니다.
*   **프로젝트별 관리:**
    *   각 사용자가 여러 문제 해결 세션을 프로젝트 단위로 관리할 수 있으며, 각 프로젝트의 토론 이력 및 신뢰도 점수가 개별적으로 유지됩니다.

## 3. 아키텍처 및 기술 스택

GemPT는 견고하고 확장 가능한 아키텍처를 기반으로 구축되었습니다.

### 3.1. 아키텍처 개요

*   **클라이언트-서버 구조:** 프론트엔드는 사용자 인터페이스를 제공하며, 백엔드는 모든 AI 로직 및 데이터 처리를 담당합니다.
*   **AI 오케스트레이션:** 백엔드는 OpenAI (GPT-4o)와 Google Generative AI (Gemini 2.5 Pro)의 API를 활용하여 다단계 AI 파이프라인을 조율합니다.
*   **데이터 지속성:** 프로젝트별 AI 신뢰도 점수는 백엔드에서 JSON 파일 형태로 관리됩니다.

### 3.2. 기술 스택

*   **프론트엔드 (Frontend):**
    *   HTML5, CSS3 (Tailwind CSS)
    *   JavaScript (React - CDN 기반 임베딩)
    *   MathJax (LaTeX 수식 렌더링 라이브러리)
*   **백엔드 (Backend):**
    *   Python 3.8+ (Flask 웹 프레임워크)
    *   OpenAI Python Client (GPT-4o 연동)
    *   Google Generative AI Python Client (Gemini 2.5 Pro 연동)
    *   SerpAPI Python Client (Google Search API 연동)
    *   `dotenv` (환경 변수 관리)
    *   `Pillow` (PIL - 이미지 처리)
    *   `Flask` (웹 서버 및 API 제공)
*   **외부 API (External APIs):**
    *   OpenAI API (GPT-4o)
    *   Google Gemini API (Gemini 2.5 Pro)
    *   SerpAPI (Google Search API)

## 4. 설치 및 실행 방법

이 프로젝트를 로컬 환경에서 설정하고 실행하기 위한 지침입니다.

### 4.1. 사전 준비

*   **Python 3.8 이상** 설치
*   활성 인터넷 연결
*   OpenAI API 키, Google Gemini API 키, SerpAPI 키 발급

### 4.2. 프로젝트 설정

1.  **리포지토리 클론:**
    ```bash
    git clone https://github.com/2025-X-Thon-Team2/2025-X-Thon-Team2_kongjjagkongjjagdugeundugeun.git
    cd 2025-X-Thon-Team2_kongjjagkongjjagdugeundugeun
    ```
2.  **백엔드 디렉토리로 이동:**
    ```bash
    cd backend
    ```
3.  **Python 가상 환경 생성 및 활성화:**
    *   Windows (PowerShell):
        ```powershell
        python -m venv venv
        .\venv\Scripts\Activate.ps1
        ```
    *   macOS/Linux:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
4.  **필요한 Python 의존성 설치:**
    ```bash
    pip install -r requirements.txt
    ```
5.  **API 키 설정:**
    *   `backend` 디렉토리에 `.env.example` 파일을 복사하여 `.env`라는 이름으로 생성합니다.
    *   `.env` 파일을 열고 플레이스홀더 값을 발급받은 실제 API 키로 대체합니다.
        ```env
        # .env 예시
        OPENAI_API_KEY="sk-YOUR_OPENAI_API_KEY"
        GOOGLE_API_KEY="AIzaSy-YOUR_GOOGLE_API_KEY"
        SERPAPI_API_KEY="YOUR_SERPAPI_KEY"
        ```

### 4.3. 애플리케이션 실행

1.  **Flask 서버 시작:**
    *   `backend` 디렉토리에 있고 가상 환경이 활성화되어 있는지 확인합니다.
    *   다음 명령어를 실행합니다:
        ```bash
        flask run
        ```
    *   서버는 일반적으로 `http://127.0.0.1:5000`에서 시작됩니다.
2.  **웹 인터페이스 열기:**
    *   선호하는 웹 브라우저에서 `http://127.0.0.1:5000` URL을 엽니다.

이제 이미지 업로드, 질문 입력, AI 모델들의 문제 해결 및 토론 과정을 확인하고 신뢰도 점수를 관리할 수 있습니다.

## 5. 라이선스

(프로젝트 라이선스 정보 필요시 작성)
