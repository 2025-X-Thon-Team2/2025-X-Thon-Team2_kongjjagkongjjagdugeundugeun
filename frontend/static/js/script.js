document.addEventListener('DOMContentLoaded', () => {
    const problemForm = document.getElementById('problem-form');
    const imageUpload = document.getElementById('image-upload');
    const imagePreview = document.getElementById('image-preview');
    const submitBtn = document.getElementById('submit-btn');
    const loadingSection = document.getElementById('loading');
    const resultsSection = document.getElementById('results-section');

    // Image preview logic
    imageUpload.addEventListener('change', () => {
        const file = imageUpload.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                imagePreview.src = e.target.result;
                imagePreview.classList.remove('hidden');
            };
            reader.readAsDataURL(file);
        }
    });

    // Form submission logic
    problemForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData(problemForm);
        if (!formData.get('image').size) {
            alert('문제 이미지를 업로드해주세요.');
            return;
        }

        // UI updates for loading
        submitBtn.disabled = true;
        submitBtn.textContent = '분석 중...';
        resultsSection.classList.add('hidden');
        loadingSection.classList.remove('hidden');

        try {
            const response = await fetch('/api/solve', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            displayResults(result);

        } catch (error) {
            console.error('Error:', error);
            alert(`오류가 발생했습니다: ${error.message}`);
        } finally {
            // Restore UI
            submitBtn.disabled = false;
            submitBtn.textContent = '분석 시작';
            loadingSection.classList.add('hidden');
        }
    });

    function displayResults(result) {
        // Update scores
        document.getElementById('gpt-score').textContent = result.scores.GPT;
        document.getElementById('gemini-score').textContent = result.scores.Gemini;

        // Update winner and final answer
        document.getElementById('winner').textContent = result.winner;
        document.getElementById('final-answer').innerHTML = marked(result.final_answer); 

        // Update process timeline
        const timelineContainer = document.getElementById('process-timeline');
        timelineContainer.innerHTML = ''; // Clear previous results

        result.process.forEach(item => {
            const itemElement = document.createElement('div');
            const modelClass = item.model.toLowerCase();
            itemElement.className = `timeline-item ${modelClass}`;

            // Sanitize content before inserting
            const sanitizedContent = item.content.replace(/</g, "&lt;").replace(/>/g, "&gt;");

            itemElement.innerHTML = "`
                <h3>${item.step}</h3>
                <p class="model-name ${modelClass}">${item.model}</p>
                <div class="content"><pre><code>${sanitizedContent}</code></pre></div>
            `";
            timelineContainer.appendChild(itemElement);
        });

        resultsSection.classList.remove('hidden');
    }
});

// A simple polyfill for a Markdown-like renderer to format the output.
function marked(text) {
    if (typeof text !== 'string') return '';
    
    text = text
        .replace(/</g, "&lt;").replace(/>/g, "&gt;") 
        .replace(/### (.*)/g, '<h3>$1</h3>')
        .replace(/## (.*)/g, '<h2>$1</h2>')
        .replace(/\*\*(.*)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*)\*/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');

    return text;
}
