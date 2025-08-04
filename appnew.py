import sys
import subprocess
import time
from pathlib import Path
import os
import streamlit as st
import requests
from dotenv import load_dotenv

# ── 1. Service launcher (runs only once) ───────────────────────────────────────

ROOT = Path(__file__).resolve().parent
print(ROOT)
SERVICES = {
    "gdpr":  (ROOT / "gdpr_checker_service",     8001),
    "value": (ROOT / "business_value_service",   8002),
    "tool":  (ROOT / "tool_recommender_service", 8003),
}

@st.cache_resource
def start_services():
    procs = []
    for name, (path, port) in SERVICES.items():
        if not path.is_dir():
            st.error(f"Service folder not found: {path}")
            continue
        cmd = [
            sys.executable, "-m", "uvicorn", "app:app",
            "--host", "127.0.0.1", "--port", str(port), "--reload"
        ]
        p = subprocess.Popen(
            cmd, cwd=str(path),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        procs.append((name, p))
    # give them a moment to spin up
    time.sleep(1.5)
    return procs

start_services()

# ── 2. Config & helpers ─────────────────────────────────────────────────────────

load_dotenv(ROOT / "streamlit_app" / ".env")

GDPR_URL  = os.getenv("GDPR_SERVICE_URL",  "http://127.0.0.1:8001")
VALUE_URL = os.getenv("VALUE_SERVICE_URL", "http://127.0.0.1:8002")
TOOL_URL  = os.getenv("TOOL_SERVICE_URL",  "http://127.0.0.1:8003")

def call_service(url, payload):
    try:
        r = requests.post(url, json=payload, timeout=(3,60))
    except requests.exceptions.RequestException as e:
        st.error(f"Error calling {url}: {e}")
        return None
    if r.status_code != 200:
        st.error(f"{url} → {r.status_code}\n{r.text}")
        return None
    try:
        return r.json()
    except ValueError:
        st.error(f"{url} returned invalid JSON:\n{r.text}")
        return None

# ── 3. Original Streamlit layout & logic ────────────────────────────────────────

st.set_page_config(page_title="AI Solution Finder", layout="centered")

st.image("public/EI.png", width=72)
st.title("AI Solution Finder")
st.write(
    "Analysieren Sie Ihre täglichen Arbeitsprozesse und erhalten Sie sofort intelligente "
    "Empfehlungen für Automatisierung und Optimierung."
)

with st.expander("Beispiel-Prozesse"):
    st.markdown(
        "- **E-Mail-Bearbeitung:** Automatisches Sortieren und Tag-ging von E-Mails\n"
        "- **Daten-Reporting:** Tägliche Berichte aus Excel-Tabellen"
    )

with st.form("process"):
    desc        = st.text_area("Prozess beschreiben", "")
    uses_pd     = st.checkbox("Enthält personenbezogene Daten?")
    time_req    = st.selectbox(
        "Zeitaufwand pro Ausführung",
        ["< 15 min","15-30 min","30-60 min","1-2 h","> 2 h"]
    )
    freq        = st.selectbox(
        "Wie oft ausgeführt?",
        ["täglich","mehrmals pro Woche","wöchentlich","monatlich","seltener"]
    )
    stakeholder = st.selectbox(
        "Betroffene Person(en)",
        ["mich","mein Team","meinen Chef","Kunden","andere"]
    )
    apps        = st.text_input("Genutzte Anwendungen",   "")
    go          = st.form_submit_button("Prozess analysieren")

if go:
    with st.spinner("Analyzing…"):
        comp = call_service(f"{GDPR_URL}/check-compliance", {"description": desc})
        val  = call_service(f"{VALUE_URL}/estimate-value", {
            "time_required": time_req,
            "frequency":     freq,
            "stakeholder":   stakeholder
        })
        recs = call_service(f"{TOOL_URL}/recommend-tool", {
            "description":  desc,
            "applications": apps
        })

    if not (comp and val and recs):
        st.stop()  # errors already shown

    st.success("Analyse abgeschlossen")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.subheader("Compliance")
        mapper = {"green": st.success, "yellow": st.warning, "red": st.error}
        mapper.get(comp["gdpr_status"], st.info)(f"GDPR: {comp['gdpr_status']}")
        st.markdown(f"**Abschnitt GDPR:** {comp['gdpr_section']}")
        st.markdown("**Begründung GDPR:**")
        st.write(comp["explanations"]["gdpr"])

        mapper.get(comp["ai_act_status"], st.info)(f"EU AI Act: {comp['ai_act_status']}")
        st.markdown(f"**Abschnitt EU AI Act:** {comp['ai_act_section']}")
        st.markdown("**Begründung EU AI Act:**")
        st.write(comp["explanations"]["ai_act"])
    with c2:
        st.metric("Business Value", val["score"])
        st.write(val.get("narrative", ""))

    with c3:
        st.subheader("Tool-Empfehlung")
        for r in recs["recommendations"]:
            st.write(f"- **{r['tool']}**: {r['reason']}")

    if "premium_count" not in st.session_state:
        st.session_state.premium_count = 0

    if st.session_state.premium_count < 3:
        if st.button("Premium-Analyse anfordern"):
            st.session_state.premium_count += 1
            st.info("Premium-Analysen sind momentan nur lokal verfügbar.")
    else:
        st.warning("Premium-Analysen-Limit (3) erreicht.")
