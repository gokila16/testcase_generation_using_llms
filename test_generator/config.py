import os
from dotenv import load_dotenv
load_dotenv()
# ============================================
# PATHS  (repo-relative; matches the GitHub repo layout)
# ============================================
#   <repo_root>/
#     ├── inputs/            extracted_metadata_final.json (precomputed)
#     ├── pdfbox/            Apache PDFBox reactor (module at pdfbox/pdfbox)
#     ├── generated_files/   pipeline outputs (git-ignored)
#     └── test_generator/    this package — config.py lives here
#
# Everything resolves relative to this file, so a fresh clone just works. If your
# machine puts these elsewhere, override per-location via environment variables:
#   TG_PDFBOX_DIR  -> the pdfbox *module* dir (where tests compile/run)
#   TG_INPUTS_DIR  -> dir holding extracted_metadata_final.json
#   TG_OUTPUT_DIR  -> where generated_files/ output is written

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))           # .../test_generator
REPO_ROOT  = os.path.abspath(os.path.join(CONFIG_DIR, os.pardir))  # repo root (one up)

INPUTS_DIR = os.environ.get('TG_INPUTS_DIR', os.path.join(REPO_ROOT, 'inputs'))
PDFBOX_DIR = os.environ.get('TG_PDFBOX_DIR', os.path.join(REPO_ROOT, 'pdfbox', 'pdfbox'))
OUTPUT_DIR = os.environ.get('TG_OUTPUT_DIR', os.path.join(REPO_ROOT, 'generated_files'))
BASE_DIR   = OUTPUT_DIR

GENRATED_FILES      = os.path.join(OUTPUT_DIR, 'gemini_3.1pro_v1')
GENERATED_TESTS_DIR = os.path.join(PDFBOX_DIR, 'generated_tests_gemini_3.1pro_v1')
PROMPTS_DIR         = os.path.join(GENRATED_FILES, 'prompts')
RESPONSES_DIR       = os.path.join(GENRATED_FILES, 'responses')
RESULTS_DIR         = os.path.join(GENRATED_FILES, 'results')
RESULTS_JSON        = os.path.join(RESULTS_DIR, 'results.json')
FINAL_REPORT        = os.path.join(RESULTS_DIR, 'final_report.txt')
INPUT_JSON          = os.path.join(INPUTS_DIR, 'extracted_metadata_final.json')

# ============================================
# LLM SETTINGS
# ============================================
# Provider selects which API key + endpoint src/llm_client.py uses:
#   'vertex' -> Vertex AI OpenAI-compatible endpoint, auth via gcloud ADC
#               (no API key; uses GCP_PROJECT / GCP_LOCATION below)
#   'gemini' -> AI Studio OpenAI-compatible endpoint (uses GEMINI_API_KEY)
#   'openai' -> native OpenAI API (uses OPENAI_API_KEY)
LLM_PROVIDER    = 'vertex'
# Gemini 3.1 Pro is preview-only right now; the GA 'gemini-3.1-pro' id does not
# exist yet. On Vertex the request model is auto-prefixed to 'google/<id>'.
LLM_MODEL       = 'gemini-3.1-pro-preview'
# Vertex AI project + location (region). Gemini 3.x preview is served on 'global'.
# Auth uses Application Default Credentials (run: gcloud auth application-default login).
# Override per machine via TG_GCP_PROJECT / TG_GCP_LOCATION (or just edit here).
GCP_PROJECT     = os.environ.get('TG_GCP_PROJECT', 'sharp-quest-386514')
GCP_LOCATION    = os.environ.get('TG_GCP_LOCATION', 'global')
# OpenAI-compatible base URL for the 'gemini' provider only. For 'vertex' the URL
# is derived from GCP_PROJECT/GCP_LOCATION; for native OpenAI set to None.
LLM_BASE_URL    = 'https://generativelanguage.googleapis.com/v1beta/openai/'
# API keys for the non-Vertex providers (read from .env if set).
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")
# Max tokens in the model's response.
LLM_MAX_TOKENS  = 16384
# Sampling temperature (0 = deterministic).
LLM_TEMPERATURE = 0
# Reasoning effort: 'low' | 'medium' | 'high'. Controls how many "thinking"
# tokens Gemini spends. Thinking tokens are billed at the output rate, so lower
# = cheaper. Leave unset/None to use the model default.
LLM_REASONING_EFFORT = 'low'
API_SLEEP_SEC   = 1
MAX_RETRIES = 2

# ============================================
# MAVEN SETTINGS
# ============================================
TEST_TIMEOUT  = 30
MAVEN_TIMEOUT = 60
# Machine-specific tool locations. Each prefers an environment variable so
# collaborators don't have to edit this file:
#   - Leave MAVEN_EXECUTABLE empty ('') if 'mvn' is on PATH. Otherwise set
#     TG_MAVEN_EXECUTABLE (or edit the fallback) to the full path of mvn / mvn.cmd.
#   - JAVA_HOME prefers your shell's JAVA_HOME; the fallback is only used if unset.
MAVEN_EXECUTABLE = os.environ.get(
    'TG_MAVEN_EXECUTABLE',
    r'C:\Program Files\maven\apache-maven-3.9.14-bin\apache-maven-3.9.14\bin\mvn.cmd')
JAVA_HOME = os.environ.get('JAVA_HOME', r'C:\Program Files\Java\ms-25.0.2')
