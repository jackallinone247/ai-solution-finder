import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage





load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("Missing OPENAI_API_KEY")

app = FastAPI(title="GDPR & EU AI Act Checker")

# --- vectorstore setup ---
vs_dir = "vectorstore"
emb = OpenAIEmbeddings()
if os.path.exists(vs_dir):
    vs = Chroma(persist_directory=vs_dir, embedding_function=emb)
else:
    docs = []
    for fn in ["data/GDPR.pdf", "data/EU_AI_Act.pdf"]:
        loader = PyPDFLoader(fn)
        pages = loader.load_and_split(RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200))
        docs.extend(pages)
    vs = Chroma.from_documents(docs, emb, persist_directory=vs_dir)
    vs.persist()

class Request(BaseModel):
    description: str

class Response(BaseModel):
    gdpr_status: str
    gdpr_section: str
    ai_act_status: str
    ai_act_section: str
    explanations: dict

@app.post("/check-compliance", response_model=Response)
async def check_compliance(req: Request):
    docs = vs.similarity_search(req.description, k=5)
    excerpts = "\n\n".join(d.page_content for d in docs)
    prompt = f"""
You are a compliance expert. Given these legal excerpts and a process description, determine:
1) GDPR compliance (“green”/“yellow”/“red”) and cite the exact GDPR Article/Section
2) EU AI Act status (“ok”/“warning”/“violation”) and cite the eact Article/Section.

Legal Excerpts:
{excerpts}

Process Description:
\"\"\"{req.description}\"\"\"

Return STRICT JSON:
{{
  "gdpr_status": <string>,
  "gdpr_section": <string>,
  "ai_act_status": <string>,
  "ai_act_section": <string>,
  "explanations": {{
    "gdpr": <string>,
    "ai_act": <string>
  }}
}}
"""
    client = ChatOpenAI(temperature=0)
    reply = client.predict_messages([
        SystemMessage(content=prompt),
        HumanMessage(content="Respond with the JSON only.")
    ])
    try:
        return Response.parse_raw(reply.content)
    except Exception as e:
        raise HTTPException(500, f"LLM response parse error: {e}")
