import time
import anthropic
import config

# The Anthropic client also reads ANTHROPIC_API_KEY from the environment by
# default; passing it explicitly keeps the source of truth in config.py.
client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

_CONTINUATION_PROMPT = (
    "Continue the Java code from exactly where you stopped. "
    "Output only the remaining Java code. "
    "No explanations, no markdown fences, no package declaration — "
    "only the code that comes after where you stopped."
)


def _system_param(system):
    """
    Wraps the static instruction text in a single cached system block so repeat
    calls reuse it at ~10% of input cost (Anthropic prompt caching). The block is
    identical for every call of a given type, so it is written once per 5-minute
    window and read by every subsequent call. Returns NOT_GIVEN to omit the
    system field entirely when no static text is supplied.
    """
    if not system:
        return anthropic.NOT_GIVEN
    return [{
        "type": "text",
        "text": system,
        "cache_control": {"type": "ephemeral"},
    }]


def _extract_text(response):
    """Concatenates all text blocks from a Message, or returns None."""
    try:
        parts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
        return "".join(parts) if parts else None
    except Exception:
        return None


def _create(system_param, messages):
    return client.messages.create(
        model=config.LLM_MODEL,
        max_tokens=config.LLM_MAX_TOKENS,
        temperature=config.LLM_TEMPERATURE,
        system=system_param,
        messages=messages,
    )


def _log_usage(response, method_name):
    """Prints cache hit/miss counts so caching can be verified during a run."""
    u = getattr(response, "usage", None)
    if not u:
        return
    print(
        f"  [cache] read={getattr(u, 'cache_read_input_tokens', 0)} "
        f"write={getattr(u, 'cache_creation_input_tokens', 0)} "
        f"fresh={getattr(u, 'input_tokens', 0)} "
        f"out={getattr(u, 'output_tokens', 0)}"
    )


def call_llm(prompt, method_name=None, system=None):
    """
    Calls Claude with the given user prompt.

    Args:
        prompt:      the per-call user content (volatile, method-specific text).
        method_name: label used for logging only.
        system:      static instruction text for this call type. Sent as a cached
                     system block; pass None to send no system block (the
                     `_simple` pipeline calls this way and still works).

    If the model hits its token limit mid-output (stop_reason == "max_tokens"),
    sends a single continuation turn in the same conversation and concatenates
    the two responses.

    Returns:
        (text: str | None, was_truncated: bool)
        was_truncated is True whenever a max_tokens truncation was detected,
        regardless of whether the continuation call succeeded.
    """
    system_param = _system_param(system)
    user_messages = [{"role": "user", "content": prompt}]

    try:
        response = _create(system_param, user_messages)
        time.sleep(config.API_SLEEP_SEC)
        _log_usage(response, method_name)

        text = _extract_text(response)

        if response.stop_reason == "max_tokens":
            label = method_name or "unknown"
            print(f"  [TRUNCATED] {label} response was cut off, requesting continuation")

            # Multi-turn continuation: the partial assistant turn is followed by a
            # user turn, so this is ordinary history, NOT an assistant prefill
            # (prefills are rejected on the 4.6 family). The same cached system
            # block is reused, so the continuation call also gets a cache hit.
            cont_messages = [
                {"role": "user",      "content": prompt},
                {"role": "assistant", "content": text or ""},
                {"role": "user",      "content": _CONTINUATION_PROMPT},
            ]
            try:
                cont = _create(system_param, cont_messages)
                cont_text = _extract_text(cont)
                if cont_text:
                    text = (text or "") + "\n" + cont_text
            except Exception as cont_e:
                print(f"  [TRUNCATED] Continuation call failed: {cont_e}")
                # Fall through — return whatever partial text we have.

            return text, True

        return text, False

    except anthropic.RateLimitError:
        # The SDK already retries 429s with backoff; this is a last-resort wait.
        print("  Rate limit hit. Waiting 60 seconds...")
        time.sleep(60)
        try:
            response = _create(system_param, user_messages)
            return _extract_text(response), False
        except Exception as e2:
            print(f"  Retry failed: {e2}")
            return None, False

    except anthropic.APIError as e:
        print(f"  API Error FULL DETAILS: {type(e).__name__}: {e}")
        return None, False

    except Exception as e:
        print(f"  Unexpected error: {type(e).__name__}: {e}")
        return None, False
