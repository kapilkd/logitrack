import json
import os
import re

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

_MODEL = "claude-sonnet-4-6"


def _client():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set.")
    return anthropic.Anthropic(api_key=api_key)


def process_email_with_claude(email_row):
    """
    Analyse a logistics email and return structured insights.
    Returns a dict with keys: summary, detected_category, extracted_entities,
    shipment_reference, invoice_reference, processing_status.
    """
    if not ANTHROPIC_AVAILABLE:
        return {
            "error": "anthropic package not installed",
            "processing_status": "FAILED",
        }

    subject = email_row["subject"] or "(no subject)"
    body = (email_row["body_plain"] or email_row["body_html"] or "(empty body)")[:3000]
    from_email = email_row["from_email"] or ""

    prompt = f"""You are a logistics email analyst. Analyse this email and return ONLY a valid JSON object with these exact keys:

- "summary": 2-3 sentence plain-text summary
- "detected_category": one of SHIPMENT_UPDATE, INVOICE, VENDOR_COMM, CUSTOMS, OTHER
- "extracted_entities": a JSON object with arrays: shipment_numbers, invoice_numbers, dates, vendor_names, amounts
- "shipment_reference": the most prominent shipment number/reference string, or null
- "invoice_reference": the most prominent invoice number string, or null

Email to analyse:
From: {from_email}
Subject: {subject}

{body}

Return only the JSON object, no markdown, no explanation."""

    try:
        msg = _client().messages.create(
            model=_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text.strip()

        # Strip markdown code fences if present
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        result = json.loads(text)

        # Normalise extracted_entities to a JSON string for DB storage
        entities = result.get("extracted_entities", {})
        if isinstance(entities, dict):
            result["extracted_entities"] = json.dumps(entities)

        result["processing_status"] = "DONE"
        return result

    except json.JSONDecodeError:
        # Attempt to salvage a JSON fragment
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
                entities = result.get("extracted_entities", {})
                if isinstance(entities, dict):
                    result["extracted_entities"] = json.dumps(entities)
                result["processing_status"] = "DONE"
                return result
            except Exception:
                pass
        return {
            "summary": text[:500],
            "detected_category": "OTHER",
            "extracted_entities": "{}",
            "shipment_reference": None,
            "invoice_reference": None,
            "processing_status": "FAILED",
        }
    except Exception as exc:
        return {
            "error": str(exc),
            "processing_status": "FAILED",
        }


def generate_reply_with_claude(thread_emails, tone="professional"):
    """
    Generate a suggested reply body for an email thread.
    thread_emails: list of email row dicts, most recent first.
    Returns a plain-text string (the reply body) or raises RuntimeError.
    """
    if not ANTHROPIC_AVAILABLE:
        raise RuntimeError("anthropic package not installed")

    # Build readable thread context (up to 3 most-recent emails)
    context_parts = []
    for e in thread_emails[:3]:
        sender = e["from_email"] or "Unknown"
        subj = e["subject"] or "(no subject)"
        body = (e["body_plain"] or "")[:800]
        context_parts.append(f"From: {sender}\nSubject: {subj}\n\n{body}")

    thread_context = "\n\n---\n\n".join(context_parts)

    prompt = f"""You are a professional logistics coordinator drafting a reply email.

Tone: {tone}

Email thread (most recent first):
{thread_context}

Write a concise reply body only. Do not include a subject line, salutation header, or your name. Start directly with the response content. Keep it under 150 words."""

    msg = _client().messages.create(
        model=_MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()
