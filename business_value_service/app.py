import os
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("Missing OPENAI_API_KEY")

app = FastAPI(title="Business Value Calculator")

class Request(BaseModel):
    time_required: str
    frequency: str
    stakeholder: str

class Response(BaseModel):
    score: float
    breakdown: dict
    narrative: str

@app.post("/estimate-value", response_model=Response)
async def estimate_value(req: Request):
    prompt = f"""
You are a process consultant. Compute a numeric business‐value score from these inputs, then give the factor breakdown and a short narrative.

Inputs:
- time_required: {req.time_required}
- frequency: {req.frequency}
- stakeholder: {req.stakeholder}

Return STRICT JSON:
{{
  "score": <float>,
  "breakdown": {{
    "time_factor": <float>,
    "frequency_factor": <float>,
    "stakeholder_factor": <float>
  }},
  "narrative": "<string>"
}}
"""
    client = ChatOpenAI(temperature=0)
    reply = client.predict_messages([
        SystemMessage(content=prompt),
        HumanMessage(content="JSON only.")
    ])
    return Response.parse_raw(reply.content)
