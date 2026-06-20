import time
from openai import OpenAI
import config

# For 'vertex' we authenticate with a gcloud ADC access token instead of an API
# key. The token expires (~1h), so we keep the credentials object around and
# refresh it before each call (see _ensure_auth) to survive long runs.
_vertex_creds = None


def _vertex_base_url():
    """OpenAI-compatible endpoint URL for the configured Vertex project/region."""
    proj = config.GCP_PROJECT
    loc  = config.GCP_LOCATION
    host = ('https://aiplatform.googleapis.com' if loc == 'global'
            else f'https://{loc}-aiplatform.googleapis.com')
    return f'{host}/v1/projects/{proj}/locations/{loc}/endpoints/openapi'


def _make_client():
    """Build an OpenAI-SDK client for the configured provider.

    - 'vertex' -> Vertex AI OpenAI-compatible endpoint, auth via gcloud ADC token
    - 'gemini' -> AI Studio OpenAI-compatible endpoint, auth via GEMINI_API_KEY
    - 'openai' -> native OpenAI endpoint, auth via OPENAI_API_KEY
    """
    global _vertex_creds
    provider = getattr(config, "LLM_PROVIDER", "openai")
    base_url = getattr(config, "LLM_BASE_URL", None)

    if provider == "vertex":
        import google.auth
        import google.auth.transport.requests as gtr
        _vertex_creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"])
        _vertex_creds.refresh(gtr.Request())
        return OpenAI(api_key=_vertex_creds.token, base_url=_vertex_base_url())

    if provider == "gemini":
        api_key = config.GEMINI_API_KEY
    else:
        api_key = config.OPENAI_API_KEY
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


client = _make_client()


def _ensure_auth():
    """Refresh the Vertex ADC access token (and the client's api_key) when it is
    near expiry, so multi-hour runs don't start failing with 401. No-op for
    API-key providers."""
    if _vertex_creds is None:
        return
    if not _vertex_creds.valid:
        import google.auth.transport.requests as gtr
        _vertex_creds.refresh(gtr.Request())
        client.api_key = _vertex_creds.token


# ---- Token usage / cost tracking ---------------------------------------
# Running totals accumulated across every call_llm() invocation in this
# process. Each _generate() call (initial, continuation, or rate-limit retry)
# is one billable request and is recorded here.
_usage_totals = {
    'calls': 0,
    'prompt_tokens': 0,
    'completion_tokens': 0,
    'reasoning_tokens': 0,
    'total_tokens': 0,
}


def _reasoning_tokens(usage, prompt, completion, total):
    """Tokens spent 'thinking'. Gemini bills these but the OpenAI-compat
    endpoint leaves completion_tokens_details null and omits them from
    completion_tokens, so we recover them from the totals. If a provider ever
    populates the explicit field, prefer it."""
    details = getattr(usage, 'completion_tokens_details', None)
    explicit = getattr(details, 'reasoning_tokens', None) if details else None
    if explicit is not None:
        return explicit
    return max(0, total - prompt - completion)


def _record_usage(response):
    """Add one API response's token usage to the running totals."""
    usage = getattr(response, 'usage', None)
    if usage is None:
        return
    prompt     = getattr(usage, 'prompt_tokens', 0) or 0
    completion = getattr(usage, 'completion_tokens', 0) or 0
    total      = getattr(usage, 'total_tokens', 0) or 0
    reasoning  = _reasoning_tokens(usage, prompt, completion, total)
    _usage_totals['calls']             += 1
    _usage_totals['prompt_tokens']     += prompt
    _usage_totals['completion_tokens'] += completion
    _usage_totals['reasoning_tokens']  += reasoning
    _usage_totals['total_tokens']      += total


def usage_with_cost(calls, prompt_tokens, completion_tokens, reasoning_tokens, total_tokens):
    """Build a usage dict augmented with USD cost from config pricing.

    Reasoning ('thinking') tokens are billed at the output rate, so output cost
    is charged on completion_tokens + reasoning_tokens.
    """
    in_rate  = getattr(config, 'LLM_INPUT_COST_PER_1M', 0) or 0
    out_rate = getattr(config, 'LLM_OUTPUT_COST_PER_1M', 0) or 0
    output_tokens_billed = completion_tokens + reasoning_tokens
    input_cost  = prompt_tokens        / 1_000_000 * in_rate
    output_cost = output_tokens_billed / 1_000_000 * out_rate
    return {
        'calls': calls,
        'prompt_tokens': prompt_tokens,
        'completion_tokens': completion_tokens,
        'reasoning_tokens': reasoning_tokens,
        'output_tokens_billed': output_tokens_billed,
        'total_tokens': total_tokens,
        'input_cost_usd':  round(input_cost, 6),
        'output_cost_usd': round(output_cost, 6),
        'total_cost_usd':  round(input_cost + output_cost, 6),
    }


def get_usage_totals():
    """Return this run's accumulated token usage plus computed USD cost."""
    return usage_with_cost(
        _usage_totals['calls'],
        _usage_totals['prompt_tokens'],
        _usage_totals['completion_tokens'],
        _usage_totals['reasoning_tokens'],
        _usage_totals['total_tokens'],
    )


_CONTINUATION_PROMPT = (
    "Continue the Java code from exactly where you stopped. "
    "Output only the remaining Java code. "
    "No explanations, no markdown fences, no package declaration — "
    "only the code that comes after where you stopped."
)


def _is_reasoning_model(model):
    """gpt-5* and o-series models are reasoning models: they only accept the
    default temperature and use `max_completion_tokens`/`reasoning_effort`."""
    m = (model or "").lower()
    return m.startswith(("gpt-5", "o1", "o3", "o4")) and "chat" not in m


def _to_messages(prompt_contents):
    """Normalize a str prompt or an existing messages list into chat messages."""
    if isinstance(prompt_contents, str):
        return [{"role": "user", "content": prompt_contents}]
    return prompt_contents


def _extract_text(response):
    """Safely extracts the assistant message text from a ChatCompletion."""
    try:
        return response.choices[0].message.content
    except Exception:
        return None


def _is_max_tokens(response):
    """Returns True if the first choice was cut off by the token limit."""
    try:
        return response.choices[0].finish_reason == "length"
    except Exception:
        return False


def _generate(prompt_contents):
    """Single chat completion call — prompt_contents may be a str or a messages list."""
    provider = getattr(config, "LLM_PROVIDER", "openai")
    effort   = getattr(config, "LLM_REASONING_EFFORT", None)
    _ensure_auth()  # refresh Vertex token if needed (no-op otherwise)

    # Vertex addresses Gemini as a publisher model: 'google/<model-id>'.
    model = config.LLM_MODEL
    if provider == "vertex" and not model.startswith("google/"):
        model = "google/" + model

    google_compat = provider in ("gemini", "vertex")

    kwargs = {
        "model": model,
        "messages": _to_messages(prompt_contents),
    }

    # Google's OpenAI-compatible endpoints expect `max_tokens`; native OpenAI
    # reasoning models require `max_completion_tokens`.
    if google_compat:
        kwargs["max_tokens"] = config.LLM_MAX_TOKENS
    else:
        kwargs["max_completion_tokens"] = config.LLM_MAX_TOKENS

    if google_compat:
        # Gemini accepts a temperature AND an optional reasoning_effort
        # ('low' | 'medium' | 'high') that controls how many thinking tokens it
        # spends. Thinking tokens are billed at the output rate, so lowering
        # this directly lowers cost.
        kwargs["temperature"] = config.LLM_TEMPERATURE
        if effort:
            kwargs["reasoning_effort"] = effort
    elif _is_reasoning_model(config.LLM_MODEL):
        # OpenAI reasoning models reject a custom temperature; pass effort instead.
        if effort:
            kwargs["reasoning_effort"] = effort
    else:
        kwargs["temperature"] = config.LLM_TEMPERATURE

    return client.chat.completions.create(**kwargs)


def call_llm(prompt, method_name=None):
    """
    Calls the OpenAI Chat Completions API with the given prompt.

    If the model hits its token limit mid-output (finish_reason == "length"),
    sends a single continuation turn in the same conversation and concatenates
    the two responses.

    Returns:
        (text: str | None, was_truncated: bool)
        was_truncated is True whenever a token-limit truncation was detected,
        regardless of whether the continuation call succeeded.
    """
    try:
        response = _generate(prompt)
        _record_usage(response)
        time.sleep(config.API_SLEEP_SEC)

        text = _extract_text(response)

        if _is_max_tokens(response):
            label = method_name or 'unknown'
            print(f"  [TRUNCATED] {label} response was cut off, requesting continuation")

            # Multi-turn continuation: give the model full context so it knows
            # exactly where it stopped.
            user_text = prompt if isinstance(prompt, str) else str(prompt)
            continuation_messages = [
                {"role": "user",      "content": user_text},
                {"role": "assistant", "content": text or ""},
                {"role": "user",      "content": _CONTINUATION_PROMPT},
            ]
            try:
                cont_response = _generate(continuation_messages)
                _record_usage(cont_response)
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
        if '429' in error_str or 'rate limit' in error_str.lower() or 'RESOURCE_EXHAUSTED' in error_str:
            print("  Rate limit hit. Waiting 60 seconds...")
            time.sleep(60)
            try:
                response = _generate(prompt)
                _record_usage(response)
                return _extract_text(response), False
            except Exception as e2:
                print(f"  Retry failed: {e2}")
                return None, False

        print(f"  API Error FULL DETAILS: {type(e).__name__}: {e}")
        return None, False
