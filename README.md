# 2025-X-Thon-Team2_kongjjagkongjjagdugeundugeun - 교차검증AI

이 프로젝트는 두 AI 모델인 ChatGPT와 Gemini가 서로의 답변을 토론하고 평가하여 사용자의 질문에 가장 신뢰도 높은 답변을 제공하는 교차 검증 시스템입니다.

## 프로젝트 구조

이 프로젝트는 프론트엔드와 백엔드로 나뉩니다.

### 백엔드

*   **위치**: `/backend`
*   **기술**: Node.js, Express
*   **설명**: 백엔드 서버는 핵심 로직을 처리합니다. 사용자 질문을 받고, OpenAI 및 Gemini API를 조회하며, 교차 검증 프로세스를 관리하고, 신뢰도 점수를 계산하여 결과와 로그를 프론트엔드에 제공합니다.

**주요 디렉토리 및 파일:**
*   `server.js`: Express 서버의 메인 진입점입니다.
*   `src/api/routes/`: API 경로 정의를 포함합니다 (예: `/ask`, `/verify`).
*   `src/services/`: 외부 AI API(OpenAI, Gemini)와 통신하는 모듈을 포함합니다.
*   `src/logic/`: 핵심 검증 및 신뢰도 점수 로직을 구현합니다.
*   `src/models/`: 프로젝트 및 로그의 데이터 구조를 정의합니다.
*   `.env.example`: 필요한 환경 변수(`PORT`, `OPENAI_API_KEY`, `GEMINI_API_KEY`)를 위한 예제 파일입니다.

### 프론트엔드

*   **위치**: `/frontend`
*   **기술**: React, Vite
*   **설명**: 프론트엔드는 시스템과 상호 작용하기 위한 사용자 인터페이스를 제공합니다. 사용자가 질문을 하고 AI 토론을 시각화할 수 있습니다.

**주요 디렉토리 및 파일:**
*   `public/index.html`: 메인 HTML 파일입니다.
*   `src/index.jsx`: React 애플리케이션의 진입점입니다.
*   `src/App.jsx`: 메인 애플리케이션 컴포넌트입니다.
*   `src/components/`: React 컴포넌트를 포함합니다:
    *   `InputForm.jsx`: 사용자가 질문을 제출하기 위한 폼입니다.
    *   `TugOfWar.jsx`: 두 AI 간의 신뢰도 경쟁을 시각화하는 컴포넌트입니다.
    *   `LogDisplay.jsx`: 검증 프로세스의 상세 로그를 표시하는 컴포넌트입니다.
*   `src/services/`: 백엔드에 API 호출을 하기 위한 함수를 포함합니다.

## 시작하기

1.  **백엔드**:
    *   `/backend` 디렉토리로 이동합니다.
    *   `.env.example` 파일로 `.env` 파일을 만들고 API 키를 추가합니다.
    *   `npm install`을 실행하여 종속성을 설치합니다.
    *   `npm start`를 실행하여 서버를 시작합니다.

2.  **프론트엔드**:
    *   `/frontend` 디렉토리로 이동합니다.
    *   `npm install`을 실행하여 종속성을 설치합니다.
    *   `npm run dev`를 실행하여 개발 서버를 시작합니다.