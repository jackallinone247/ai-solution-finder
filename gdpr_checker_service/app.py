import os , json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.schema import SystemMessage, HumanMessage



# ── Load API key ──────────────────────────────────────────────────────────────
load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("Missing OPENAI_API_KEY")

app = FastAPI(title="GDPR & EU AI Act Checker")

# ── Build or load vectorstore of your PDFs ───────────────────────────────────
VS_DIR = "vectorstore"
emb = OpenAIEmbeddings()
if os.path.isdir(VS_DIR):
    vs = Chroma(persist_directory=VS_DIR, embedding_function=emb)
else:
    pages = []
    for fn in ("data/GDPR.pdf", "data/EU_AI_Act.pdf"):
        if not os.path.isfile(fn):
            raise RuntimeError(f"Missing PDF: {fn}")
        loader = PyPDFLoader(fn)
        pages.extend(
            loader.load_and_split(
                RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            )
        )
    vs = Chroma.from_documents(pages, emb, persist_directory=VS_DIR)
    vs.persist()

# ── Define request/response schema ───────────────────────────────────────────
class Request(BaseModel):
    description: str

class Response(BaseModel):
    gdpr_status:    str   # "green"/"yellow"/"red"
    gdpr_section:   str   # exact article or "-"
    ai_act_status:  str   # "ok"/"warning"/"violation"
    ai_act_section: str   # exact article or "-"
    explanations:   dict  # { "gdpr": "...", "ai_act": "..." }

# ── The single endpoint ──────────────────────────────────────────────────────
@app.post("/check-compliance", response_model=Response)
async def check_compliance(req: Request):
    # 1) Retrieve the top-5 relevant law chunks
    docs = vs.similarity_search(req.description, k=5)
    excerpts = "\n\n".join(d.page_content for d in docs)

    # 2) Build a prompt that first asks: “Is this AI?” then classify
    system = """
Du bist ein Compliance-Experte, der sich auf DSGVO und EU AI Act spezialisiert hat.
Arbeite *ausschließlich* mit den folgenden Auszügen aus den Originalgesetzestexten:

{excerpts}
"""
    user = f"""
1. Entscheide zuerst, ob dieses Projekt Künstliche Intelligenz verwendet (z.B. Machine Learning, LLMs, Automatisierungs-Frameworks). 
   - Wenn JA: setze "ai_used": "yes" und begründe in ein bis zwei Sätzen.
   - Wenn NEIN: setze "ai_used": "no" und begründe in ein bis zwei Sätzen.

2. Kategorisiere gemäß DSGVO:
   - gdpr_status: "green"/"yellow"/"red"
   - gdpr_section: exakte Artikelnummer oder "-"

3. Kategorisiere gemäß EU AI Act:
   - Wenn ai_used="yes": ai_act_status: "warning"/"violation" und ai_act_section: exakte Artikelnummer
   - Wenn ai_used="no": ai_act_status: "ok" und ai_act_section: "-"

4. Gib STRICT JSON zurück mit exakt diesen Feldern:
{{
  "gdpr_status":    <string>,
  "gdpr_section":   <string>,
  "ai_act_status":  <string>,
  "ai_act_section": <string>,
  "explanations": {{
    "gdpr":   <string>,
    "ai_act": <string>
  }}
}}

Bewerte nun die Anfrage:
\"\"\"{req.description}\"\"\"
"""

    prompt_sys = SystemMessage(content=system.format(excerpts=excerpts))
    prompt_user = HumanMessage(content=user)

    try:
        client = ChatOpenAI(temperature=0, model_name="gpt-4o-mini")
        reply = client.predict_messages([prompt_sys, prompt_user])
        raw = reply.content.strip()
    except Exception as e:
        raise HTTPException(500, f"LLM request failed: {e}")

    # 3) Parse JSON
    try:
        return Response.parse_raw(raw)
    except Exception as e:
        raise HTTPException(
            500,
            f"JSON parse error: {e}\n\nResponse was:\n{raw}"
        )
