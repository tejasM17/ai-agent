# Medi-Sync AI Triage System ⚕️

Medi-Sync is an intelligent medical triage system powered by a multi-agent AI pipeline. It analyzes patient symptoms using real-time medical research, reflects on findings for accuracy, and generates a prioritized clinical report.

## 🚀 System Architecture
- **Backend:** FastAPI, LangChain, Google Gemini (Multi-Agent Pipeline), DuckDuckGo Search.
- **Frontend:** React-based dashboard for real-time monitoring and reporting.
- **Agents:** Researcher (Search), Reviewer (Reflection), and Triage Officer (Structured Output).

---

## 🛠️ Backend Setup (ai-agent)
**Repo:** `https://github.com/SharathKumar-M/ai-agent`

### 1. Prerequisites
- Python 3.9+
- Google Gemini API Key ([Get it here](https://aistudio.google.com/app/apikey))

### 2. Installation
```bash
git clone https://github.com/SharathKumar-M/ai-agent.git
cd ai-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install ddgs pytest httpx  # Ensure latest tools are installed
```

### 3. Environment Configuration
Create a `.env` file in the root directory:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 4. Running the Server
```bash
python main.py
```
The backend will be available at `http://localhost:8000`.

---

## 💻 Frontend Setup (medi-sync)
**Repo:** `https://github.com/tejasM17/medi-sync`

### 1. Installation
```bash
git clone https://github.com/tejasM17/medi-sync.git
cd medi-sync

# Install dependencies
npm install
```

### 2. Configuration
Ensure the API base URL in your frontend code points to `http://localhost:8000`.

### 3. Running the App
```bash
npm start
```
The frontend will be available at `http://localhost:3000`.

---

## 📡 API Endpoints Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/incoming-patient` | Submit symptoms to start the AI triage. |
| `GET` | `/api/ai-logs` | **Live Stream** (SSE) of agent thinking process. |
| `GET` | `/api/incoming-patient`| Fetch history of all triage cases. |
| `GET` | `/api/reports/{id}` | Generate a professional medical report. |
| `GET` | `/health` | Check backend system status. |

---

## 🔍 Features & Workflow
1. **Submit Symptoms:** Post patient data via the frontend form.
2. **Live Monitoring:** The `/api/ai-logs` endpoint streams agent activity line-by-line using Server-Sent Events (SSE).
3. **Multi-Agent Logic:** 
   - **Researcher** fetches clinical guidelines from the web.
   - **Reviewer** critiques the research for potential gaps.
   - **Triage Officer** makes the final decision on urgency.
4. **Download Report:** Generate a clinical-grade report with structured data once the AI finishes.

## 🧪 Testing
Run the backend test suite to verify endpoint integrity:
```bash
python -m pytest test_main.py
```

## 📄 License
This project is for educational and clinical support purposes. Always consult a qualified medical professional for actual medical advice.
