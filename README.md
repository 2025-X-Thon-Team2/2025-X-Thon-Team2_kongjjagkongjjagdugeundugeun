# GemPT: AI-Powered Dual Verification System

GemPT is a web application that leverages a dual-AI model system to provide and verify solutions to problems submitted via images. It uses OpenAI's GPT model as the primary "Solver" and Google's Gemini model as the "Verifier" to create a high-stakes debate loop, ensuring the final answer is robust and accurate.

## Features

- **Image-based Problem Submission**: Users can upload an image of a problem.
- **Dual-AI Verification**: GPT-4o provides an initial solution, which is then audited by Gemini for correctness and logical fallacies.
- **Debate Loop**: If a discrepancy is found, the models engage in a multi-round debate to resolve the issue.
- **Credit Scoring System**: A dynamic scoring system tracks the credibility of each AI model based on its performance.
- **Interactive UI**: A clean and simple frontend to upload images, ask questions, and view the detailed debate process.

## Project Structure
```
.
├── backend/
│   ├── .env.example          # Example for environment variables
│   ├── app.py                # Main Flask application
│   ├── project_db.json       # Database file for scores
│   ├── requirements.txt      # Python dependencies
│   └── venv/                 # Python virtual environment (ignored by git)
├── frontend/
│   ├── index.html            # Main HTML file
│   └── static/
│       ├── css/style.css     # Stylesheet
│       └── js/script.js      # JavaScript for frontend logic
└── .gitignore
└── README.md
```

## Getting Started

Follow these instructions to set up and run the project on your local machine.

### 1. Prerequisites

- Python 3.8 or higher
- An active internet connection
- API keys for both OpenAI and Google Gemini

### 2. Setup

**a. Clone the repository:**
```bash
git clone https://github.com/2025-X-Thon-Team2/2025-X-Thon-Team2_kongjjagkongjjagdugeundugeun.git
cd 2025-X-Thon-Team2_kongjjagkongjjagdugeundugeun
```

**b. Navigate to the backend directory:**
```bash
cd backend
```

**c. Create and activate a Python virtual environment:**
- For Windows (PowerShell):
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- For macOS/Linux:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

**d. Install the required dependencies:**
```bash
pip install -r requirements.txt
```

**e. Set up your API keys:**
- In the `backend` directory, create a copy of `.env.example` and name it `.env`.
- Open the `.env` file with a text editor.
- Replace the placeholder values with your actual API keys.

  ```env
  # .env
  OPENAI_API_KEY="sk-..."
  GOOGLE_API_KEY="AIzaSy..."
  ```

### 3. Running the Application

**a. Start the Flask server:**
- Make sure you are in the `backend` directory and your virtual environment is activated.
- Run the following command:
  ```bash
  flask run
  ```

**b. Open the web interface:**
- The server will start, typically on `http://127.0.0.1:5000`.
- Open this URL in your web browser.

You can now upload an image, ask a question, and see the AI models work to find a solution.
