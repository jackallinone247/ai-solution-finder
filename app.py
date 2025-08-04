import os
import streamlit as st
import requests
from dotenv import load_dotenv

load_dotenv()
GDPR_URL  = os.getenv("GDPR_SERVICE_URL",  "http://localhost:8001")
VALUE_URL = os.getenv("VALUE_SERVICE_URL", "http://localhost:8002")
TOOL_URL  = os.getenv("TOOL_SERVICE_URL",  "http://localhost:8003")

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
    time_req    = st.selectbox("Zeitaufwand pro Ausführung", ["< 15 min","15-30 min","30-60 min","1-2 h","> 2 h"])
    freq        = st.selectbox("Wie oft ausgeführt?",    ["täglich","mehrmals pro Woche","wöchentlich","monatlich","seltener"])
    stakeholder = st.selectbox("Betroffene Person(en)",   ["mich","mein Team","meinen Chef","Kunden","andere"])
    apps        = st.text_input("Genutzte Anwendungen",   "")
    go          = st.form_submit_button("Prozess analysieren")

if go:
    payload = {
        "description":       desc,
        "usesPersonalData":  uses_pd,
        "timeRequired":      time_req,
        "frequency":         freq,
        "stakeholder":       stakeholder,
        "applications":      apps,
    }

    with st.spinner("Analyzing…"):
        comp = requests.post(f"{GDPR_URL}/check-compliance", json={"description": desc}).json()
        val  = requests.post(f"{VALUE_URL}/estimate-value", json={
            "time_required": time_req,
            "frequency":     freq,
            "stakeholder":   stakeholder
        }).json()
        recs = requests.post(f"{TOOL_URL}/recommend-tool", json={
            "description":  desc,
            "applications": apps
        }).json()

    st.success("Analyse abgeschlossen")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.subheader("Compliance")
        if comp["gdpr_status"] == "green":
            st.success(f"GDPR: {comp['gdpr_status']}")
        elif comp["gdpr_status"] == "yellow":
            st.warning(f"GDPR: {comp['gdpr_status']}")
        else:
            st.error(f"GDPR: {comp['gdpr_status']}")

        if comp["ai_act_status"] == "ok":
            st.success(f"EU AI Act: {comp['ai_act_status']}")
        elif comp["ai_act_status"] == "warning":
            st.warning(f"EU AI Act: {comp['ai_act_status']}")
        else:
            st.error(f"EU AI Act: {comp['ai_act_status']}")

    with c2:
        st.metric("Business Value", val["score"])
        st.write(val["narrative"])

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
