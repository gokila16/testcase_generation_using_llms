import time
from openai import OpenAI
import config

# DeepSeek serves an OpenAI-compatible API, so the OpenAI SDK works unchanged —
# only api_key and base_url differ. The call/response contract
# (call_llm(prompt) -> text | None) is identical, so the rest of the pipeline is
# untouched.
client = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_BASE_URL)


def _is_reasoning_model(model):
    """Reasoning models use a different API contract: max_completion_tokens (not
    max_tokens) and only the default temperature. Covers OpenAI gpt-5/o-series and
    DeepSeek's reasoner. deepseek-chat (the v1 default) is NOT a reasoning model,
    so it takes the standard max_tokens + temperature branch."""
    m = (model or '').lower()
    return (m.startswith('gpt-5') or m.startswith('o1') or m.startswith('o3')
            or m.startswith('o4') or 'reasoner' in m)


def _build_request_kwargs(prompt):
    model = config.LLM_MODEL
    kwargs = {
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
    }
    if _is_reasoning_model(model):
        # Reasoning models: token budget covers reasoning + output; no custom temperature.
        kwargs['max_completion_tokens'] = config.LLM_MAX_TOKENS
        effort = getattr(config, 'LLM_REASONING_EFFORT', None)
        if effort:
            kwargs['reasoning_effort'] = effort
    else:
        kwargs['max_tokens'] = config.LLM_MAX_TOKENS
        kwargs['temperature'] = config.LLM_TEMPERATURE
    return kwargs


def call_llm(prompt):
    """
    Calls OpenAI API with the given prompt.
    Handles rate limits and errors gracefully.
    Returns raw response text or None if failed.
    """
    try:
        response = client.chat.completions.create(**_build_request_kwargs(prompt))
        # Sleep to avoid rate limits
        time.sleep(config.API_SLEEP_SEC)
        return response.choices[0].message.content

    except Exception as e:
        error_str = str(e)

        # Rate limit — wait and retry once
        if '429' in error_str:
            print("  Rate limit hit. Waiting 60 seconds...")
            time.sleep(60)
            try:
                response = client.chat.completions.create(**_build_request_kwargs(prompt))
                return response.choices[0].message.content
            except Exception as e2:
                print(f"  Retry failed: {e2}")
                return None

        print(f"  API Error FULL DETAILS: {type(e).__name__}: {e}")
        return None
