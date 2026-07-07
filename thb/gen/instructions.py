"""Instruction document generator.

Turns a list of (step_template, kwargs) pairs into a realistic operational
document in EN/DE/AR. Framing (title wording, preamble) varies per seed so
no global phrase is shared across tasks, but the numbered steps themselves
are direct and deterministic. Every document is screened against the banned
phrase list at build time.
"""

from typing import Any, Dict, List, Optional, Tuple

from ..artifacts.files import markdown_doc
from ..artifacts.multilingual import render_numbered
from ..core.naming import contains_banned_phrase
from ..core.rng import TaskRng

Step = Tuple[str, Dict[str, Any]]

_PREAMBLES = {
    "en": [
        "Processing notes for this batch. Work through the items in order.",
        "Operational record. Execute the numbered items exactly as written.",
        "Runbook extract. Each numbered item depends on the previous one.",
        "Review checklist. Complete the items strictly in sequence.",
    ],
    "de": [
        "Bearbeitungsnotizen für diesen Lauf. Arbeite die Punkte der Reihe nach ab.",
        "Betriebsprotokoll. Führe die nummerierten Punkte exakt wie beschrieben aus.",
        "Auszug aus dem Runbook. Jeder Punkt baut auf dem vorherigen auf.",
    ],
    "ar": [
        "ملاحظات المعالجة لهذه الدفعة. نفّذ البنود بالترتيب.",
        "سجل تشغيلي. نفّذ البنود المرقمة كما هي مكتوبة تمامًا.",
        "مقتطف من دليل التشغيل. كل بند يعتمد على البند الذي قبله.",
    ],
}

_TITLE_WORDS = ["survey", "ledger", "rollout", "ingest", "review", "batch",
                "record", "digest"]


def doc_title(rng: TaskRng, label: str, run_tag: str) -> str:
    word = rng.choice("title_word:" + label, _TITLE_WORDS)
    return "%s %s %s" % (run_tag, word, rng.code("title_code:" + label, 3))


def build_instruction_markdown(
        rng: TaskRng, label: str, run_tag: str, steps: List[Step],
        lang: str = "en",
        front_matter: Optional[Dict[str, Any]] = None,
        extra_sections: Optional[List[Dict[str, str]]] = None) -> str:
    """Build one instruction document; raises if a banned phrase slips in."""
    preamble = rng.choice("preamble:%s:%s" % (label, lang), _PREAMBLES[lang])
    sections = [{"heading": "", "body": preamble},
                {"heading": "", "body": render_numbered(steps, lang)}]
    if extra_sections:
        sections.extend(extra_sections)
    text = markdown_doc(doc_title(rng, label, run_tag), sections,
                        front_matter=front_matter)
    hit = contains_banned_phrase(text)
    if hit:
        raise ValueError("banned phrase %r in generated instructions" % hit)
    return text
