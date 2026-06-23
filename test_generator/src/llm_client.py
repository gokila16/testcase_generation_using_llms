import time
from openai import OpenAI
import config

# Provider-aware LLM client. The default provider is 'vertex' (Google Vertex AI,
# OpenAI-compatible endpoint), which authenticates with a gcloud Application
# Default Credentials (ADC) access token instead of an API key. That token
# expires (~1h), so we keep the credentials object around and refresh it before
# each call (see _ensure_auth) to survive long runs.
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
    provider = getattr(config, "LLM_PROVIDER", "vertex")
    base_url = getattr(config, "LLM_BASE_URL", None)

    if provider == "vertex":
        import google.auth
        import google.auth.transport.requests as gtr
        _vertex_creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"])
        _vertex_creds.refresh(gtr.Request())
        return OpenAI(api_key=_vertex_creds.token, base_url=_vertex_base_url())

    if provider == "gemini":
        return OpenAI(api_key=config.GEMINI_API_KEY, base_url=base_url)

    # native OpenAI
    return OpenAI(api_key=config.OPENAI_API_KEY)


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


def _generate(prompt):
    """Single chat-completion call. Returns the assistant message text (or None)."""
    provider = getattr(config, "LLM_PROVIDER", "vertex")
    effort   = getattr(config, "LLM_REASONING_EFFORT", None)
    _ensure_auth()  # refresh Vertex token if needed (no-op otherwise)

    # Vertex addresses Gemini as a publisher model: 'google/<model-id>'.
    model = config.LLM_MODEL
    if provider == "vertex" and not model.startswith("google/"):
        model = "google/" + model

    kwargs = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": config.LLM_MAX_TOKENS,
        "temperature": config.LLM_TEMPERATURE,
    }
    # Gemini accepts an optional reasoning_effort ('low' | 'medium' | 'high')
    # that controls how many thinking tokens it spends; lowering it lowers cost.
    if provider in ("vertex", "gemini") and effort:
        kwargs["reasoning_effort"] = effort

    response = client.chat.completions.create(**kwargs)
    try:
        return response.choices[0].message.content
    except Exception:
        return None


def call_llm(prompt):
    """
    Calls the configured LLM (default: Vertex AI Gemini) with the given prompt.
    Handles rate limits and errors gracefully.
    Returns raw response text or None if failed.
    """
    try:
        text = _generate(prompt)
        # Sleep to avoid rate limits
        time.sleep(config.API_SLEEP_SEC)
        return text

    except Exception as e:
        error_str = str(e)

        # Rate limit / quota exhausted — wait and retry once
        if '429' in error_str or 'rate limit' in error_str.lower() or 'RESOURCE_EXHAUSTED' in error_str:
            print("  Rate limit hit. Waiting 60 seconds...")
            time.sleep(60)
            try:
                return _generate(prompt)
            except Exception as e2:
                print(f"  Retry failed: {e2}")
                return None

        print(f"  API Error FULL DETAILS: {type(e).__name__}: {e}")
        return None
