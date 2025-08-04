import os
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("Missing OPENAI_API_KEY")

app = FastAPI(title="Tool Recommendation Selector")

class Request(BaseModel):
    description: str
    applications: str

class Recommendation(BaseModel):
    tool: str
    reason: str

class Response(BaseModel):
    recommendations: list[Recommendation]

@app.post("/recommend-tool", response_model=Response)
async def recommend_tool(req: Request):
    prompt = f"""
You are an automation architect. Recommend the top 3 tools (with reasons) for this process.

Process Description:
\"\"\"{req.description}\"\"\"

Existing Applications:
{req.applications}

Return STRICT JSON:
{{
  "recommendations": [
    {{ "tool": "<name>", "reason": "<why>" }},
    {{ "tool": "<name>", "reason": "<why>" }},
    {{ "tool": "<name>", "reason": "<why>" }}
  ]
}}
"""
    client = ChatOpenAI(temperature=0)
    reply = client.predict_messages([
        SystemMessage(content=prompt),
        HumanMessage(content="JSON only.")
    ])
    return Response.parse_raw(reply.content)
