"""
DocuSentinel AI - LLM Service
Supports any OpenAI-compatible API: OpenAI, Groq, Together, Ollama, etc.

Environment variables:
    LLM_API_KEY      required — your API key
    LLM_MODEL        required — model name e.g. "llama-3.3-70b-versatile"
    LLM_BASE_URL     optional — e.g. "https://api.groq.com/openai/v1"
                                    or "http://localhost:11434/v1" (Ollama)

If LLM_API_KEY is not set, all calls return an explicit NOT_CONFIGURED error.
The system NEVER pretends to be an LLM when no key is present.
"""

import json
import logging
import re
from typing import Optional
from backend.config import get_settings

logger = logging.getLogger("docusentinel.llm")
settings = get_settings()


class LLMNotConfiguredError(Exception):
    """Raised when no API key is present."""
    pass


class LLMCallError(Exception):
    """Raised when the LLM call fails (timeout, rate-limit, invalid key, etc.)."""
    pass


def get_llm_status() -> dict:
    """
    Returns the actual LLM status — never lies.
    Used by /api/health.
    """
    key = settings.effective_llm_api_key
    if not key:
        return {
            "status": "NOT_CONFIGURED",
            "message": "LLM_API_KEY is not set in backend/.env",
            "model": None,
        }
    return {
        "status": "CONFIGURED",
        "message": f"Model: {settings.llm_model} | Base: {settings.llm_base_url or 'OpenAI default'}",
        "model": settings.llm_model,
    }


def call_llm(
    system_prompt: str,
    user_message: str,
    json_mode: bool = False,
    max_retries: int = 1,
) -> str:
    """
    Call the configured LLM synchronously.

    Returns the assistant response text.
    Raises LLMNotConfiguredError if no API key.
    Raises LLMCallError on API failure (after retries).
    """
    key = settings.effective_llm_api_key
    if not key:
        raise LLMNotConfiguredError(
            "LLM_API_KEY is not configured. "
            "Add LLM_API_KEY=<your_key> to backend/.env to enable AI-powered answers. "
            "Get a free key at https://console.groq.com (Groq) or https://platform.openai.com"
        )

    last_error: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            import httpx
            import json as _json

            base_url = settings.llm_base_url or "https://api.openai.com/v1"
            base_url = base_url.rstrip("/")

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ]

            body: dict = {
                "model":       settings.llm_model,
                "messages":    messages,
                "temperature": settings.llm_temperature,
                "max_tokens":  settings.llm_max_tokens,
            }
            if json_mode:
                body["response_format"] = {"type": "json_object"}

            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type":  "application/json",
            }

            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=body,
                )

            if resp.status_code == 401:
                raise LLMCallError(
                    "Invalid API key (401 Unauthorized). "
                    "Check LLM_API_KEY in backend/.env"
                )
            if resp.status_code == 429:
                raise LLMCallError(
                    "Rate limit exceeded (429). Wait a moment and try again."
                )
            if resp.status_code >= 400:
                raise LLMCallError(
                    f"LLM API error {resp.status_code}: {resp.text[:200]}"
                )

            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            logger.info(f"LLM call OK (attempt {attempt+1}): {len(content)} chars")
            return content

        except (LLMNotConfiguredError, LLMCallError):
            raise
        except Exception as e:
            last_error = e
            logger.warning(f"LLM call attempt {attempt+1} failed: {e}")

    raise LLMCallError(
        f"LLM call failed after {max_retries+1} attempt(s): {last_error}"
    )


def call_llm_for_investigation(
    question: str,
    evidence_context: str,
    conflict_note: str = "",
) -> dict:
    """
    Call LLM for an investigation and parse the structured JSON response.
    Returns a dict with keys: answer, status, confidence, reasoning_summary.
    Raises LLMNotConfiguredError or LLMCallError on failure.
    """
    system_prompt = """You are DocuSentinel AI, an evidence-first document investigation assistant.

CRITICAL RULES — follow without exception:
1. Answer ONLY using the evidence chunks supplied below. Do NOT use outside knowledge.
2. Never invent facts, dates, names, numbers, or relationships not in the evidence.
3. If evidence is contradictory, explicitly report BOTH values and label it CONFLICTING.
4. If evidence is absent or insufficient, return NOT_FOUND or UNCERTAIN — never guess.
5. Every factual claim must cite its supporting document name and page number.

Return a JSON object with these exact keys:
{
  "answer": "<clear natural language answer citing sources>",
  "status": "<VERIFIED | CONFLICTING | UNCERTAIN | NOT_FOUND>",
  "confidence": <integer 0-100>,
  "reasoning_summary": "<one sentence explaining the confidence and status>"
}

Status definitions:
- VERIFIED: multiple evidence sources agree on a clear answer
- CONFLICTING: evidence sources disagree — report all values
- UNCERTAIN: some evidence exists but is incomplete or ambiguous
- NOT_FOUND: no relevant evidence in the supplied chunks"""

    user_message = (
        f"QUESTION: {question}\n\n"
        f"{evidence_context}"
        f"{conflict_note}\n\n"
        "Respond with a JSON object as specified. "
        "Be specific about source document names and page numbers in your answer."
    )

    raw = call_llm(system_prompt, user_message, json_mode=True)

    # Parse and validate the JSON response
    try:
        parsed = json.loads(raw)
        # Validate required keys
        answer      = str(parsed.get("answer", "")).strip()
        status      = str(parsed.get("status", "UNCERTAIN")).strip().upper()
        confidence  = int(parsed.get("confidence", 50))
        reasoning   = str(parsed.get("reasoning_summary", "")).strip()

        if status not in ("VERIFIED", "CONFLICTING", "UNCERTAIN", "NOT_FOUND"):
            status = "UNCERTAIN"
        confidence = max(0, min(100, confidence))

        if not answer:
            answer = "The LLM returned an empty answer. Please try again."

        return {
            "answer":   answer,
            "status":   status,
            "confidence": confidence,
            "reasoning_summary": reasoning,
        }

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning(f"LLM JSON parse failed: {e}. Raw: {raw[:200]}")
        # Retry without JSON mode to get a plain-text answer
        try:
            plain = call_llm(
                system_prompt.replace("Return a JSON object", "Return plain text"),
                user_message,
                json_mode=False,
                max_retries=0,
            )
            return {
                "answer":    plain,
                "status":    "UNCERTAIN",
                "confidence": 40,
                "reasoning_summary": "LLM returned unstructured response; confidence reduced.",
            }
        except Exception:
            raise LLMCallError(
                f"LLM returned malformed JSON and plain-text retry also failed: {e}"
            )
