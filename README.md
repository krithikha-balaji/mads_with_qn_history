# Multi-Agent Debate System - Website Simulation

This is a web-based simulation of the six-agent debate workflow. Groq generates the agent responses; the orchestration simulates independent proposals, debate/critique, consensus scoring and final aggregation.

## Structure
backend/main.py
backend/requirements.txt
backend/.env.example
frontend/index.html

## Run in VS Code PowerShell

1. Extract the ZIP and open the `multi-agent-debate-website` folder in VS Code.

2. Open a terminal and enter:
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks activation:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

3. Create `backend/.env` (not `.env.txt`) with:
```env
GROQ_API_KEY=your_real_groq_key
```

4. Start the backend:
```powershell
uvicorn main:app --reload
```
Keep this terminal open.

5. Open `frontend/index.html` in a browser. For easiest use, install the VS Code Live Server extension, then right-click `index.html` -> `Open with Live Server`.

6. Enter any question and click Start Debate.

The page displays all six agents, their proposals, debate critiques/counterarguments, consensus scores and a definite final answer with justification.

Do not share or commit `.env`.
