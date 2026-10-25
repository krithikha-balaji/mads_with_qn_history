import os, json, re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

app = FastAPI(title="Multi-Agent Debate System")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

ROLES = [
    ("Problem Solver Agent", "Solve the problem directly with a practical, logical answer."),
    ("Critical Analyst Agent", "Challenge assumptions and identify weaknesses, risks, contradictions and edge cases."),
    ("Domain Expert Agent", "Use relevant domain knowledge and explain important principles."),
    ("Fact Checker Agent", "Separate reliable claims from assumptions and flag uncertain statements."),
    ("Alternative Solution Agent", "Propose different approaches and compare them with the main approach."),
    ("Strategy Agent", "Focus on implementation, trade-offs, priorities and the best practical strategy.")
]

class DebateRequest(BaseModel):
    question: str


def extract_json(text):
    text = re.sub(r"```json|```", "", text).strip()

    try:
        data = json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.S)
        if match:
            try:
                data = json.loads(match.group(0))
            except Exception:
                return None
        else:
            return None

    # The AI may return a list containing dictionaries.
    if isinstance(data, list):
        data = next(
            (item for item in data if isinstance(item, dict)),
            None
        )

    # All debate stages expect a JSON object.
    if isinstance(data, dict):
        return data

    return None


def call_llm(system, user):
    if not API_KEY:
        raise HTTPException(500, "GROQ_API_KEY is missing. Create backend/.env and add your key.")
    try:
        client = Groq(api_key=API_KEY)
        r = client.chat.completions.create(
            model=MODEL, temperature=0.35,
            messages=[{"role":"system","content":system},{"role":"user","content":user}]
        )
        return r.choices[0].message.content
    except Exception as e:
        raise HTTPException(500, f"Groq API error: {e}")

def safe_int(v, default=70):
    try: return max(0, min(100, int(v)))
    except Exception: return default

def make_agent(role, instruction, question):
    raw = call_llm(
        f"""You are the {role} in a simulated multi-agent debate.
{instruction}
Return ONLY valid JSON:
agent, proposal, arguments (array of strings), assumptions (array of strings), justification, confidence (integer 0-100).""",
        f"Question: {question}"
    )
    d = extract_json(raw) or {}
    return {
        "agent": role,
        "proposal": d.get("proposal", raw),
        "arguments": d.get("arguments", []),
        "assumptions": d.get("assumptions", []),
        "justification": d.get("justification", "Reasoned analysis by the agent."),
        "confidence": safe_int(d.get("confidence",70))
    }

@app.get("/")
def root():
    return {"status":"ok","message":"Backend running"}

@app.post("/api/debate")
def debate(req: DebateRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "Question cannot be empty.")

    proposals = [make_agent(r,i,question) for r,i in ROLES]
    context = "\n\n".join(
        f"{p['agent']}:\nProposal: {p['proposal']}\nArguments: {p['arguments']}\nConfidence: {p['confidence']}%"
        for p in proposals
    )

    critiques = []
    for role,_ in ROLES:
        raw = call_llm(
            f"""You are the {role} in a simulated debate.
Review the six proposals. Identify strengths and weaknesses, give counterarguments,
and state your revised position. Return ONLY valid JSON:
agent, strong_arguments (array), weak_arguments (array), criticisms (array),
counterarguments (array), revised_position, confidence (integer 0-100).""",
            f"Question: {question}\n\n{context}"
        )
        d = extract_json(raw) or {}
        critiques.append({
            "agent": role,
            "strong_arguments": d.get("strong_arguments", []),
            "weak_arguments": d.get("weak_arguments", []),
            "criticisms": d.get("criticisms", []),
            "counterarguments": d.get("counterarguments", []),
            "revised_position": d.get("revised_position", ""),
            "confidence": safe_int(d.get("confidence",70))
        })

    scores = []
    for p,c in zip(proposals,critiques):
        aq = min(100, 60 + 8*len(p["arguments"]) + 4*len(c["strong_arguments"]) - 3*len(c["weak_arguments"]))
        score = 0.35*aq + 0.30*p["confidence"] + 0.20*c["confidence"] + 0.15*aq
        scores.append({
            "agent":p["agent"], "argument_quality":round(aq,1),
            "agent_confidence":p["confidence"], "debate_confidence":c["confidence"],
            "consensus_score":round(score,1)
        })

    debate_context = "\n\n".join(
        f"{c['agent']}: Revised position: {c['revised_position']}; "
        f"Criticisms: {c['criticisms']}; Counterarguments: {c['counterarguments']}"
        for c in critiques
    )

    raw = call_llm(
        """You are the final Consensus Engine and Answer Aggregator.
Synthesize the debate into ONE definite answer. Never stop without final_answer.
Return ONLY valid JSON:
final_answer, justification (array), selected_arguments (array),
major_criticisms_considered (array), consensus_result, overall_confidence (integer 0-100).""",
        f"Question: {question}\n\nInitial proposals:\n{context}\n\nDebate:\n{debate_context}\n\nScores:\n{scores}"
    )
    final = extract_json(raw) or {}
    final.setdefault("final_answer", "The agents reached a reasoned consensus based on the strongest arguments.")
    final.setdefault("justification", [])
    final.setdefault("selected_arguments", [])
    final.setdefault("major_criticisms_considered", [])
    final.setdefault("consensus_result", "Consensus selected the strongest arguments after critique and revision.")
    final["overall_confidence"] = safe_int(final.get("overall_confidence",85),85)

    return {"question":question,"proposals":proposals,"critiques":critiques,"scores":scores,"final":final}
