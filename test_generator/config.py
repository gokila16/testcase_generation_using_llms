import os
from dotenv import load_dotenv

# Everything resolves relative to the repo root, so the pipeline runs on any
# machine without editing paths. This file lives in <repo>/test_generator/.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(_THIS_DIR)

load_dotenv(os.path.join(REPO_ROOT, '.env'))

# ---------------------------------------------------------------------------
# MODEL SELECTION
# Set exactly ONE flag to True. The resolver below picks the matching entry
# from MODELS and exposes it as LLM_PROVIDER / LLM_MODEL / etc.
# ---------------------------------------------------------------------------
USE_GEMINI_3_5_FLASH = False
USE_GEMINI_3_1_PRO   = False
USE_GPT_5_MINI       = False
USE_GPT_5_5          = False
USE_DEEPSEEK_4_PRO   = True
USE_DEEPSEEK_4_FLASH = False

# provider: "vertex"   -> Google Vertex AI via the google-genai SDK (gcloud ADC auth)
#           "openai"   -> OpenAI native API (OPENAI_API_KEY)
#           "deepseek" -> DeepSeek's OpenAI-compatible API (DEEPSEEK_API_KEY)
# effort:   reasoning/thinking effort for reasoning models (None = not applicable)
MODELS = {
    "gemini-3.5-flash": {
        "provider": "vertex",
        "model":    "gemini-3.5-flash",
        "location": "us-central1",
        "effort":   "medium",
    },
    "gemini-3.1-pro": {
        "provider": "vertex",
        "model":    "gemini-3.1-pro-preview",  # TODO: confirm; switch to "gemini-3.1-pro" at GA
        "location": "global",                  # 3.1 Pro serves only on the global endpoint
        "effort":   "medium",
    },
    "gpt-5-mini": {
        "provider":    "openai",
        "model":       "gpt-5-mini",
        "base_url":    None,
        "api_key_env": "OPENAI_API_KEY",
        "effort":      "medium",
    },
    "gpt-5.5": {
        "provider":    "openai",
        "model":       "gpt-5.5",
        "base_url":    None,
        "api_key_env": "OPENAI_API_KEY",
        "effort":      "medium",
    },
    "deepseek-v4-pro": {
        "provider":    "deepseek",
        "model":       "deepseek-v4-pro",
        "base_url":    "https://api.deepseek.com",
        "api_key_env": "DEEPSEEK_API_KEY",
        "effort":      None,
    },
    "deepseek-v4-flash": {
        "provider":    "deepseek",
        "model":       "deepseek-v4-flash",
        "base_url":    "https://api.deepseek.com",
        "api_key_env": "DEEPSEEK_API_KEY",
        "effort":      None,
    },
}

_MODEL_FLAGS = {
    "USE_GEMINI_3_5_FLASH": "gemini-3.5-flash",
    "USE_GEMINI_3_1_PRO":   "gemini-3.1-pro",
    "USE_GPT_5_MINI":       "gpt-5-mini",
    "USE_GPT_5_5":          "gpt-5.5",
    "USE_DEEPSEEK_4_PRO":   "deepseek-v4-pro",
    "USE_DEEPSEEK_4_FLASH": "deepseek-v4-flash",
}

_enabled = [key for flag, key in _MODEL_FLAGS.items() if globals()[flag]]
if len(_enabled) != 1:
    raise ValueError(
        f"Exactly one USE_* model flag must be True, found {len(_enabled)}: {_enabled or 'none'}. "
        f"Edit the flags at the top of config.py."
    )

ACTIVE_MODEL = _enabled[0]
_active      = MODELS[ACTIVE_MODEL]

LLM_PROVIDER = _active["provider"]
LLM_MODEL    = _active["model"]
LLM_EFFORT   = _active.get("effort")
LLM_BASE_URL = _active.get("base_url")
LLM_API_KEY  = os.getenv(_active["api_key_env"]) if _active.get("api_key_env") else None

# Vertex AI (Gemini) — auth via gcloud Application Default Credentials.
#   gcloud auth application-default login
#   gcloud config set project <your-project>
# Per-model "location" above wins; otherwise fall back to env / global.
VERTEX_PROJECT  = os.getenv("GOOGLE_CLOUD_PROJECT")
VERTEX_LOCATION = _active.get("location") or os.getenv("GOOGLE_CLOUD_LOCATION", "global")

# Slug used to namespace this model's outputs so runs never overwrite each other.
_MODEL_SLUG = ACTIVE_MODEL.replace('.', '-').replace('/', '-')

PDFBOX_REPO = os.path.join(REPO_ROOT, 'pdfbox')          # multi-module Maven repo root (bundled)
PDFBOX_DIR  = os.path.join(PDFBOX_REPO, 'pdfbox')        # the actual pdfbox Maven module
INPUTS_DIR  = os.path.join(REPO_ROOT, 'inputs')          # bundled precomputed inputs

# Repo-local outputs (git-ignored, regenerated on every run), namespaced per model.
GENRATED_FILES      = os.path.join(REPO_ROOT, 'generated_files', 'zeroshot', _MODEL_SLUG)
GENERATED_TESTS_DIR = os.path.join(PDFBOX_DIR, f'generated_tests_zeroshot_{_MODEL_SLUG}')
PROMPTS_DIR         = os.path.join(GENRATED_FILES, 'prompts')
RESPONSES_DIR       = os.path.join(GENRATED_FILES, 'responses')
RESULTS_DIR         = os.path.join(GENRATED_FILES, 'results')
RESULTS_JSON        = os.path.join(RESULTS_DIR, 'results.json')
FINAL_REPORT        = os.path.join(RESULTS_DIR, 'final_report.txt')

INPUT_JSON          = os.path.join(INPUTS_DIR, 'extracted_metadata_final.json')

LLM_MAX_TOKENS  = 16384
LLM_TEMPERATURE = 0
API_SLEEP_SEC   = 1

TEST_TIMEOUT  = 30
MAVEN_TIMEOUT = 60
# Set these in .env only if Maven / the JDK are not already on PATH.
#   MAVEN_EXECUTABLE=C:\Program Files\apache-maven-3.9.x\bin\mvn.cmd
#   JAVA_HOME=C:\Program Files\Java\jdk-21
MAVEN_EXECUTABLE = os.getenv("MAVEN_EXECUTABLE")
JAVA_HOME        = os.getenv("JAVA_HOME")
