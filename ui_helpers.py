# ui_helpers.py
import streamlit as st
from pathlib import Path

# Centralized translations (only German for now)
TEXTS = {
    "header": "AI Solution Finder",
    "subheader": "Analysieren Sie Ihre täglichen Arbeitsprozesse und erhalten Sie sofort intelligente Empfehlungen für Automatisierung und Optimierung.",
    "desc": "Prozess beschreiben",
    "apps": "Anwendungen",
    "time_req": "Zeitaufwand pro Ausführung",
    "freq": "Wie oft ausgeführt?",
    "stakeholder": "Betroffene Person(en)",
    "uses_pd": "Enthält personenbezogene Daten?",
    "submit": "Prozess analysieren",
    "premium": "Premium-Analyse anfordern",
}

def get_text(key: str) -> str:
    return TEXTS.get(key, key)

def load_css():
    css_path = Path("styles/styles.css")
    if css_path.exists():
        css = css_path.read_text()
        st.markdown(f"<style>\n{css}\n</style>", unsafe_allow_html=True)

def render_placeholders():
    ph = {
        "compliance": st.empty(),
        "value": st.empty(),
        "tools": st.empty(),
    }
    return ph
