from __future__ import annotations

import json
import os
from typing import Optional

from openai import OpenAI
from pydantic import ValidationError

from .models import ActionItem, Decision, ExtractionResult


SYSTEM_PROMPT = """You are an expert at extracting decisions and action items from meeting notes and transcripts.

Rules:
1. Only extract things that were clearly *decided* or *assigned*. Do not invent items.
2. A Decision is a choice the group made (e.g. "We will drop phone verification").
3. An Action Item is concrete work with (ideally) an owner and a deadline.
4. Prefer short, precise language. Remove filler.
5. Always attach a short evidence quote or paraphrase from the source text.
6. If ownership is unclear, set owner to null rather than guessing a name.
7. If a deadline is relative ("next Friday", "end of month"), keep the original phrase in due_text and try to normalize due_date only when confident.
8. Return valid JSON matching the schema. No extra commentary.
"""


EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "meeting_summary": {"type": "string"},
        "decisions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "evidence": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["text"],
            },
        },
        "action_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "owner": {"type": ["string", "null"]},
                    "due_text": {"type": ["string", "null"]},
                    "evidence": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["text"],
            },
        },
    },
    "required": ["decisions", "action_items"],
}


def extract(
    text: str,
    meeting_id: str,
    *,
    model: str = "gpt-4o-mini",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> ExtractionResult:
    """Run extraction against the given meeting text."""

    client_kwargs = {}
    if api_key:
        client_kwargs["api_key"] = api_key
    if base_url:
        client_kwargs["base_url"] = base_url

    # Falls back to OPENAI_API_KEY / ANTHROPIC etc. via environment
    client = OpenAI(**client_kwargs)

    user_content = f"""Meeting text:\n\n{text}\n\nExtract decisions and action items. Return only JSON."""

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

    # Attach meeting_id and build full models
    decisions = []
    for d in data.get("decisions", []):
        decisions.append(
            Decision(
                meeting_id=meeting_id,
                text=d["text"],
                evidence=d.get("evidence"),
                confidence=float(d.get("confidence", 0.8)),
            )
        )

    actions = []
    for a in data.get("action_items", []):
        actions.append(
            ActionItem(
                meeting_id=meeting_id,
                text=a["text"],
                owner=a.get("owner"),
                due_text=a.get("due_text"),
                evidence=a.get("evidence"),
                confidence=float(a.get("confidence", 0.8)),
            )
        )

    return ExtractionResult(
        decisions=decisions,
        action_items=actions,
        meeting_summary=data.get("meeting_summary"),
    )
