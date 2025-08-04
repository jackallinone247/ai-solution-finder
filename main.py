# main.py
import os
import json
import logging
import threading
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from langchain.schema import HumanMessage
from langchain_openai import ChatOpenAI
from streamlit.components.v1 import html as st_html

from vectorstore import get_vectorstore
from prompts import (
    COMPLIANCE_SYSTEM, COMPLIANCE_TEMPLATE,
    BUSINESS_SYSTEM, BUSINESS_TEMPLATE,
    TOOL_TEMPLATE
)
from ui_helpers import get_text, load_css

# --- Logging setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Config & Secrets ---
load_dotenv()
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    st.error("OPENAI_API_KEY fehlt!")
    st.stop()
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# PDF docs from secrets or fallback
PDFS = st.secrets.get("pdf_paths", ["data/GDPR.pdf", "data/EU_AI_Act.pdf"])

from pathlib import Path
st.write("🔍 PDF paths:", PDFS)
for p in PDFS:
    st.write(f"• {p}: exists? {Path(p).exists()}")


# --- Streamlit page ---
st.set_page_config(page_title=get_text("header"), layout="wide")
load_css()
st.title(get_text("header"))
st.write(get_text("subheader"))

# Prepare vectorstore & LLM
vs = get_vectorstore(PDFS)
llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)

# --- Helpers ---
def safe_json_parse(raw: str):
    """Try to parse JSON, retry once on common errors."""
    text = raw.strip().strip("```json").strip("```")
    try:
        return json.loads(text)
    except Exception:
        import re
        cleaned = re.sub(r",\s*}", "}", re.sub(r",\s*\]", "]", text))
        return json.loads(cleaned)

# --- Form ---
with st.form("process"):
    left, right = st.columns([2.5, 1.5])
    with left:
        desc = st.text_area(get_text("desc"), height=125)
        apps = st.text_area(get_text("apps"), height=75)
    with right:
        st.markdown("<div style='margin-top:2rem'></div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2, gap="small")
        with c1:
            time_req = st.selectbox(
                "Zeitaufwand pro Ausführung",
                ["< 15 min", "15-30 min", "30-60 min", "1-2 h", "> 2 h"]
            )
            stakeholder = st.selectbox(
                "Betroffene Person(en)",
                ["mich", "mein Team", "meinen Chef", "Kunden", "andere"]
            )
        with c2:
            freq    = st.selectbox(
                "Wie oft ausgeführt?",
                ["täglich", "mehrmals pro Woche", "wöchentlich", "monatlich", "seltener"]
            )
            uses_pd = st.selectbox(
                "Enthält personenbezogene Daten?",
                ["Nein", "Ja"]
            )
        go = st.form_submit_button(get_text("submit"))

if go:
    if not desc.strip():
        st.warning("Bitte Prozessbeschreibung eingeben.")
        st.stop()

    # store results
    results = {"comp": None, "val": None, "tools": None}

    # define threaded calls
    def _call_compliance():
        docs = vs.similarity_search(desc, k=5)
        excerpts = "\n\n".join(d.page_content for d in docs)
        content = COMPLIANCE_TEMPLATE.format(excerpts=excerpts, description=desc)
        resp = llm.predict_messages([COMPLIANCE_SYSTEM, HumanMessage(content=content)])
        results["comp"] = safe_json_parse(resp.content)

    def _call_value():
        prompt = BUSINESS_TEMPLATE.format(
            time_required=time_req,
            frequency=freq,
            stakeholder=stakeholder
        )
        resp = llm.predict_messages([BUSINESS_SYSTEM, HumanMessage(content=prompt)])
        results["val"] = safe_json_parse(resp.content)

    def _call_tools():
        prompt = TOOL_TEMPLATE.format(description=desc, applications=apps)
        resp = llm.predict_messages([HumanMessage(content=prompt)])
        results["tools"] = safe_json_parse(resp.content)

    # run in parallel
    threads = [
        threading.Thread(target=_call_compliance),
        threading.Thread(target=_call_value),
        threading.Thread(target=_call_tools),
    ]

    with st.spinner("Analysiere…"):
        for t in threads: t.start()
        for t in threads: t.join()

    st.success("Analyse abgeschlossen")

    # build HTML for the three cards
    lines = [
        '<div class="report-container">',
        # Compliance card
        '<div class="card">',
        '  <h3>📋 Compliance</h3>',
        f'  <p><strong>GDPR:</strong> {results["comp"]["gdpr_status"]} '
        f'(Art. {results["comp"]["gdpr_section"]})</p>',
        f'  <p><strong>Begründung GDPR:</strong> {results["comp"]["explanations"]["gdpr"]}</p>',
        f'  <p><strong>EU AI Act:</strong> {results["comp"]["ai_act_status"]} '
        f'(Art. {results["comp"]["ai_act_section"]})</p>',
        f'  <p><strong>Begründung AI Act:</strong> {results["comp"]["explanations"]["ai_act"]}</p>',
        '</div>',

        # Business Value card
        '<div class="card">',
        '  <h3>💡 Business Value</h3>',
        f'  <p style="font-size:2rem; margin:0;">{results["val"]["score"]}</p>',
        f'  <p>{results["val"]["narrative"]}</p>',
        '</div>',

        # Tool Recommendation card
        '<div class="card">',
        '  <h3>🛠 Tool-Empfehlung</h3>',
        '  <ul class="tools-list">',
    ]
    for rec in results["tools"]["recommendations"]:
        lines.append(
            f'    <li><strong>{rec["tool"]}</strong>: {rec["reason"]}</li>'
        )
    lines += [
        '  </ul>',
        '</div>',
        '</div>',
    ]

    html_str = "\n".join(lines)

    # Render via Markdown (ensure your CSS is loaded)
    st.markdown(html_str, unsafe_allow_html=True)
    # — or, if flex still fails, uncomment below to use an HTML iframe:
    # st_html(html_str, height=400, scrolling=True)

    # Premium limiter
    if "premium" not in st.session_state:
        st.session_state.premium = 3
    if st.session_state.premium > 0:
        if st.button(get_text("premium")):
            st.session_state.premium -= 1
            st.info(f"Noch {st.session_state.premium} Premium-Analysen übrig.")
    else:
        st.warning("Premium-Limit erreicht.")
