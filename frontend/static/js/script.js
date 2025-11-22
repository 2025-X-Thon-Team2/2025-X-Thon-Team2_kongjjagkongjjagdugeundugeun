document.addEventListener('DOMContentLoaded', () => {
    // DOMContentLoaded 이벤트: HTML 문서가 완전히 로드되고 파싱된 후 스크립트가 실행되도록 합니다. (이미지 등 외부 리소스는 기다리지 않음)

    // 필요한 HTML 요소들을 JavaScript 변수로 가져옵니다. (id 속성을 이용)
    const problem_form = document.getElementById('problem-form');           // 문제 제출 폼
    const image_upload = document.getElementById('image-upload');           // 이미지 업로드 input
    const image_preview = document.getElementById('image-preview');         // 이미지 미리보기 img 태그
    const submit_btn = document.getElementById('submit-btn');               // 제출 버튼
    const loading_section = document.getElementById('loading');             // 로딩 섹션
    const results_section = document.getElementById('results-section');     // 결과 표시 섹션

    // === 이미지 미리보기 로직 ===
    image_upload.addEventListener('change', () => {
        // 이미지 파일이 선택되면(change 이벤트 발생)
        const file = image_upload.files[0]; // 선택된 파일 중 첫 번째 파일 가져오기
        if (file) { // 파일이 존재하면
            const reader = new FileReader(); // FileReader 객체 생성: 파일을 비동기적으로 읽을 수 있게 해줍니다.
            reader.onload = (e) => {
                // 파일 읽기가 완료되면 실행될 함수
                image_preview.src = e.target.result; // 읽은 파일의 URL을 이미지 미리보기의 src로 설정
                image_preview.classList.remove('hidden'); // 미리보기 이미지를 보이도록 hidden 클래스 제거
            };
            reader.readAsDataURL(file); // 파일을 Data URL (base64 인코딩) 형태로 읽기 시작
        }
    });

    // === 폼 제출 로직 ===
    problem_form.addEventListener('submit', async (e) => {
        // 폼 제출 이벤트 발생 시
        e.preventDefault(); // 기본 폼 제출 동작(페이지 새로고침)을 막습니다.

        const form_data = new FormData(problem_form); // 폼 데이터(이미지, 질문 등)를 FormData 객체로 만듭니다.
        if (!form_data.get('image').size) { // 이미지 파일이 업로드되지 않았다면 (파일 크기가 0)
            alert('문제 이미지를 업로드해주세요.'); // 경고 메시지 표시
            return; // 함수 실행 중단
        }

        // UI를 로딩 상태로 업데이트
        submit_btn.disabled = true; // 버튼 비활성화
        submit_btn.textContent = '분석 중...'; // 버튼 텍스트 변경
        results_section.classList.add('hidden'); // 이전 결과 섹션 숨기기
        loading_section.classList.remove('hidden'); // 로딩 섹션 보이기

        try {
            // 백엔드 API로 데이터를 전송합니다. (fetch API 사용)
            const response = await fetch('/api/solve', { // '/api/solve' 엔드포인트로 요청
                method: 'POST', // HTTP POST 메서드 사용 (데이터 전송)
                body: form_data, // FormData 객체를 요청 본문에 담아 보냅니다. (이미지 파일 포함)
            });

            if (!response.ok) { // 응답 상태 코드가 200번대가 아니면 (예: 404, 500 오류)
                const error_data = await response.json(); // 서버에서 보낸 에러 메시지를 JSON으로 파싱
                throw new Error(error_data.error || `HTTP error! status: ${response.status}`); // 에러 발생시키기
            }

            const result = await response.json(); // 성공적인 응답을 JSON 형태로 파싱하여 결과 받기
            display_results(result); // 받은 결과를 화면에 표시하는 함수 호출

        } catch (error) {
            console.error('Error:', error); // 콘솔에 에러 로그 출력
            alert(`오류가 발생했습니다: ${error.message}`); // 사용자에게 에러 메시지 알림
        } finally {
            // 요청이 완료되면 (성공 또는 실패와 관계없이) UI를 원래대로 복원
            submit_btn.disabled = false; // 버튼 활성화
            submit_btn.textContent = '분석 시작'; // 버튼 텍스트 원상 복구
            loading_section.classList.add('hidden'); // 로딩 섹션 숨기기
        }
    });

    // === 결과 표시 함수 ===
    function display_results(result) {
        // 점수 업데이트
        document.getElementById('gpt-score').textContent = result.scores.GPT; // ChatGPT 점수 업데이트
        document.getElementById('gemini-score').textContent = result.scores.Gemini; // Gemini 점수 업데이트

        // 승자 및 최종 답변 업데이트
        document.getElementById('winner').textContent = result.winner; // 최종 승자 표시
        // 최종 답변은 Markdown 형식일 수 있으므로, marked 함수로 HTML 변환 후 innerHTML에 삽입
        document.getElementById('final-answer').innerHTML = marked(result.final_answer); 

        // 토론 과정 타임라인 업데이트
        const timeline_container = document.getElementById('process-timeline');
        timeline_container.innerHTML = ''; // 이전에 표시된 타임라인 내용을 모두 지웁니다.

        // 백엔드에서 받은 토론 과정(result.process) 배열을 순회하며 각 단계를 화면에 추가
        result.process.forEach(item => {
            const item_element = document.createElement('div'); // 새로운 div 요소 생성
            const model_class = item.model.toLowerCase();      // 모델 이름을 소문자로 변환하여 CSS 클래스에 활용
            item_element.className = `timeline-item ${model_class}`;

            // 내용에 HTML 태그가 포함될 수 있으므로, 보안을 위해 이스케이프 처리(sanitized_content)
            // <를 &lt;로, >를 &gt;로 변환하여 스크립트 삽입 공격(XSS)을 방지합니다.
            const sanitized_content = item.content.replace(/</g, "&lt;").replace(/>/g, "&gt;");

            // 타임라인 항목의 HTML 내용을 구성
            item_element.innerHTML = `
                <h3>${item.step}</h3> <!-- 현재 단계 (예: Initial Solution, Round 1 Defense) -->
                <p class="model-name ${model_class}">${item.model}</p> <!-- 어떤 모델이 한 행동인지 표시 -->
                <div class="content"><pre><code>${sanitized_content}</code></pre></div> <!-- 모델의 답변 내용 (pre, code 태그로 포맷 유지) -->
            `;
            timeline_container.appendChild(item_element); // 생성된 타임라인 항목을 컨테이너에 추가
        });

        results_section.classList.remove('hidden'); // 결과 섹션을 보이도록 hidden 클래스 제거
    }
});

// === Markdown 형식 텍스트를 HTML로 변환하는 간단한 함수 ===
// 실제 프로덕션 환경에서는 'marked.js' 또는 'showdown.js'와 같은 라이브러리를 사용하는 것이 좋습니다.
function marked(text) {
    if (typeof text !== 'string') return ''; // 입력이 문자열이 아니면 빈 문자열 반환
    
    // 기본적인 HTML 태그 이스케이프 (보안 강화)
    text = text
        .replace(/</g, "&lt;").replace(/>/g, "&gt;") // HTML 태그를 텍스트로 변환하여 렌더링되지 않도록 함
        // Markdown 문법을 HTML 태그로 변환
        .replace(/### (.*)/g, '<h3>$1</h3>') // ### 제목 -> h3 태그
        .replace(/## (.*)/g, '<h2>$1</h2>')   // ## 제목 -> h2 태그
        .replace(/\*\*(.*)\*\*/g, '<strong>$1</strong>') // **굵게** -> strong 태그
        .replace(/\*(.*)\*/g, '<em>$1</em>')     // *기울임* -> em 태그
        .replace(/`([^`]+)`/g, '<code>$1</code>') // `코드` -> code 태그
        .replace(/\n/g, '<br>');             // 줄바꿈 문자 -> br 태그

    return text; // HTML로 변환된 문자열 반환
}