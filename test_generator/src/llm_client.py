import time
import config

# Lazily built, provider-specific client. Only one provider is active per run,
# so e.g. a DeepSeek run never needs gcloud credentials and vice-versa.
_client = None


def _openai_client():
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL)
    return _client


def _vertex_client():
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(
            vertexai=True,
            project=config.VERTEX_PROJECT,
            location=config.VERTEX_LOCATION,
        )
    return _client


def _openai_kwargs(prompt):
    kwargs = {
        'model': config.LLM_MODEL,
        'messages': [{'role': 'user', 'content': prompt}],
    }
    if config.LLM_PROVIDER == 'openai':
        # GPT-5 family: needs max_completion_tokens, only accepts the default
        # temperature, and takes reasoning effort instead.
        kwargs['max_completion_tokens'] = config.LLM_MAX_TOKENS
        if config.LLM_EFFORT:
            kwargs['reasoning_effort'] = config.LLM_EFFORT
    else:  # deepseek (OpenAI-compatible, classic params)
        kwargs['max_tokens'] = config.LLM_MAX_TOKENS
        kwargs['temperature'] = config.LLM_TEMPERATURE
    return kwargs


def _call_openai_compatible(prompt):
    response = _openai_client().chat.completions.create(**_openai_kwargs(prompt))
    return response.choices[0].message.content


def _call_vertex(prompt):
    from google.genai import types
    cfg = types.GenerateContentConfig(
        temperature=config.LLM_TEMPERATURE,
        max_output_tokens=config.LLM_MAX_TOKENS,
    )
    if config.LLM_EFFORT:
        # Gemini 3 controls reasoning via thinking_level (valid values may be
        # model-specific; "medium" per request).
        cfg.thinking_config = types.ThinkingConfig(thinking_level=config.LLM_EFFORT)
    response = _vertex_client().models.generate_content(
        model=config.LLM_MODEL,
        contents=prompt,
        config=cfg,
    )
    return response.text


_CALLERS = {
    'openai':   _call_openai_compatible,
    'deepseek': _call_openai_compatible,
    'vertex':   _call_vertex,
}


def call_llm(prompt):
    """
    Calls the active LLM (selected via the USE_* flags in config.py).
    Dispatches to the OpenAI-compatible client (OpenAI / DeepSeek) or the
    Vertex AI client (Gemini). Handles rate limits and errors gracefully.
    Returns raw response text or None if failed.
    """
    caller = _CALLERS[config.LLM_PROVIDER]
    try:
        result = caller(prompt)
        # Sleep to avoid rate limits
        time.sleep(config.API_SLEEP_SEC)
        return result

    except Exception as e:
        error_str = str(e)

        # Rate limit — wait and retry once
        if '429' in error_str or 'rate' in error_str.lower():
            print("  Rate limit hit. Waiting 60 seconds...")
            time.sleep(60)
            try:
                return caller(prompt)
            except Exception as e2:
                print(f"  Retry failed: {e2}")
                return None

        print(f"  API Error FULL DETAILS: {type(e).__name__}: {e}")
        return None
