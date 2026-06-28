import time
from openai import OpenAI
import config

# DeepSeek's API is OpenAI-compatible, so we use the openai SDK pointed at the
# DeepSeek base URL. Auth is via an API key (config.DEEPSEEK_API_KEY, loaded from
# .env). Get a key at https://platform.deepseek.com.
client = OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
)

_CONTINUATION_PROMPT = (
    "Continue the Java code from exactly where you stopped. "
    "Output only the remaining Java code. "
    "No explanations, no markdown fences, no package declaration — "
    "only the code that comes after where you stopped."
)


def _extract_text(response):
    """Safely extracts the text from a chat completion response."""
    try:
        return response.choices[0].message.content
    except Exception:
        return None


def _is_truncated(response):
    """Returns True if the first choice's finish_reason is 'length'."""
    try:
        return response.choices[0].finish_reason == 'length'
    except Exception:
        return False


def _generate(messages):
    """Single chat-completion call — messages is a list of {role, content} dicts."""
    return client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=messages,
        max_tokens=config.LLM_MAX_TOKENS,
        temperature=config.LLM_TEMPERATURE,
    )


def call_llm(prompt, method_name=None):
    """
    Calls the DeepSeek API with the given prompt.

    If the model hits its token limit mid-output (finish_reason == 'length'),
    sends a single continuation turn in the same conversation and concatenates
    the two responses.

    Returns:
        (text: str | None, was_truncated: bool)
        was_truncated is True whenever a length truncation was detected,
        regardless of whether the continuation call succeeded.
    """
    user_text = prompt if isinstance(prompt, str) else str(prompt)
    messages = [{"role": "user", "content": user_text}]

    try:
        response = _generate(messages)
        time.sleep(config.API_SLEEP_SEC)

        text = _extract_text(response)

        if _is_truncated(response):
            label = method_name or 'unknown'
            print(f"  [TRUNCATED] {label} response was cut off, requesting continuation")

            # Multi-turn continuation: give the model full context so it knows
            # exactly where it stopped.
            continuation_messages = [
                {"role": "user",      "content": user_text},
                {"role": "assistant", "content": text or ""},
                {"role": "user",      "content": _CONTINUATION_PROMPT},
            ]
            try:
                cont_response = _generate(continuation_messages)
                cont_text = _extract_text(cont_response)
                if cont_text:
                    text = (text or "") + "\n" + cont_text
            except Exception as cont_e:
                print(f"  [TRUNCATED] Continuation call failed: {cont_e}")
                # Fall through — return whatever partial text we have.

            return text, True

        return text, False

    except Exception as e:
        error_str = str(e)

        # Rate limit — wait and retry once
        if '429' in error_str or 'rate limit' in error_str.lower():
            print("  Rate limit hit. Waiting 60 seconds...")
            time.sleep(60)
            try:
                response = _generate(messages)
                return _extract_text(response), False
            except Exception as e2:
                print(f"  Retry failed: {e2}")
                return None, False

        print(f"  API Error FULL DETAILS: {type(e).__name__}: {e}")
        return None, False
