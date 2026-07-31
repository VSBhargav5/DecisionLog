from __future__ import annotations

import json
from datetime import date
from typing import Optional

from openai import OpenAI

from .dates import normalize_deadline
from .models import ActionItem, Decision, ExtractionResult


SYSTEM_PROMPT = """You are an expert at extracting *decisions* and *owned action items* from meeting notes and transcripts.

Your job is to produce a clean, accountable record — not a summary of discussion.

Rules:

1. DECISIONS
   - Only extract things the group clearly *decided* or *agreed*.
   - Ignore pure discussion, ideas, or open questions.
   - Phrase each decision as a short, definitive statement.

2. ACTION ITEMS
   - Must be concrete work someone will do.
   - Prefer explicit owners. If the text says "Sarah will..." or "John to update...", capture the name.
   - If ownership is vague ("someone should", "we need to", "the team"), set owner to null. Do not invent names.
   - Capture deadline phrases exactly as spoken ("next Friday", "end of month", "by the 15th").

3. EVIDENCE
   - Every item must include a short evidence quote or close paraphrase from the source.

4. CONFIDENCE
   - 0.9–1.0 = explicit and unambiguous
   - 0.7–0.85 = reasonably clear
   - below 0.7 = somewhat inferred (use sparingly)

5. OUTPUT
   - Return valid JSON only. No commentary.
   - Schema:
     {
       "meeting_summary": "one short sentence",
       "decisions": [{"text": "...", "evidence": "...", "confidence": 0.9}],
       "action_items": [{"text": "...", "owner": "Name or null", "due_text": "... or null", "evidence": "...", "confidence": 0.9}]
     }
"""


def extract(
    text: str,
    meeting_id: str,
    *,
    reference_date: Optional[date] = None,
    model: str = "gpt-4o-mini",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> ExtractionResult:
    """Extract decisions and action items, then normalize deadlines."""

    client_kwargs = {}
    if api_key:
        client_kwargs["api_key"] = api_key
    if base_url:
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs)

    user_content = (
        f"Meeting text:\n\n{text}\n\n"
        "Extract only clear decisions and owned action items. Return JSON."
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    raw = response.choices[0].message.content
    if not raw:
        raise RuntimeError("Empty response from model")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Model returned invalid JSON: {e}") from e

    ref = reference_date or date.today()

    decisions = [
        Decision(
            meeting_id=meeting_id,
            text=d["text"].strip(),
            evidence=(d.get("evidence") or "").strip() or None,
            confidence=float(d.get("confidence", 0.8)),
        )
        for d in data.get("decisions", [])
        if d.get("text")
    ]

    actions = []
    for a in data.get("action_items", []):
        if not a.get("text"):
            continue
        due_text = (a.get("due_text") or "").strip() or None
        due_date, _ = normalize_deadline(due_text, reference=ref)
        owner = (a.get("owner") or "").strip() or None
        # Light ownership cleanup: reject generic placeholders the model sometimes leaks
        if owner and owner.lower() in {"someone", "the team", "team", "tbd", "n/a", "null"}:
            owner = None

        actions.append(
            ActionItem(
                meeting_id=meeting_id,
                text=a["text"].strip(),
                owner=owner,
                due_text=due_text,
                due_date=due_date,
                evidence=(a.get("evidence") or "").strip() or None,
                confidence=float(a.get("confidence", 0.8)),
            )
        )

    return ExtractionResult(
        decisions=decisions,
        action_items=actions,
        meeting_summary=(data.get("meeting_summary") or "").strip() or None,
    )
