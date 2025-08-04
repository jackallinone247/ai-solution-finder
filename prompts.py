# prompts.py
from langchain import PromptTemplate
from langchain.schema import SystemMessage, HumanMessage

COMPLIANCE_SYSTEM = SystemMessage(content=(
    "Du bist ein Compliance-Experte, der *ausschließlich* auf den folgenden "
    "Gesetzestext-Auszügen aus der DSGVO und dem EU AI Act basiert."
))

COMPLIANCE_TEMPLATE = PromptTemplate.from_template("""
Auszüge:
{excerpts}

1) Entscheide, ob KI verwendet wird (“yes”/“no”) und begründe kurz.
2) Klassifiziere DSGVO:
   - gdpr_status: "green" / "yellow" / "red"
   - gdpr_section: exakte Artikelnummer oder "-"
3) Klassifiziere EU AI Act:
   - Wenn KI verwendet: ai_act_status: "ok"/"warning"/"violation", plus ai_act_section
   - Sonst: ai_act_status: "ok", ai_act_section: "-"
4) Gib NUR JSON zurück mit:
{{
  "gdpr_status":    "<string>",
  "gdpr_section":   "<string>",
  "ai_act_status":  "<string>",
  "ai_act_section": "<string>",
  "explanations": {{
    "gdpr":   "<string>",
    "ai_act": "<string>"
  }}
}}

Bewerte: """ + '"""{description}"""'
)

BUSINESS_SYSTEM = SystemMessage(content="Du bist ein erfahrener Business-Analyst.")

BUSINESS_TEMPLATE = PromptTemplate.from_template("""
Du bist ein Analyst. Berechne einen Business-Value-Score aus:
- time_required: {time_required}
- frequency: {frequency}
- stakeholder: {stakeholder}

Gib NUR JSON zurück:
{{
  "score": <float>,
  "narrative": "<string>"
}}
""")

TOOL_TEMPLATE = PromptTemplate.from_template("""
Du bist ein Automation-Architekt. Empfiehl die Top-3 Tools (mit Gründen) für:
- Beschreibung: """ + '"""{description}"""' + """
- Bestehende Apps: {applications}

Gib NUR JSON zurück:
{{
  "recommendations": [
    {{ "tool": "<string>", "reason": "<string>" }},
    {{ "tool": "<string>", "reason": "<string>" }},
    {{ "tool": "<string>", "reason": "<string>" }}
  ]
}}
""")
