import os
from dotenv import load_dotenv
load_dotenv()
# ============================================
# PATHS  (repo-relative; matches the GitHub repo layout)
# ============================================
#   <repo_root>/
#     ├── inputs/            extracted_metadata_final.json, call_graph.json
#     ├── pdfbox/            Apache PDFBox 3.0.5 reactor (module at pdfbox/pdfbox)
#     ├── generated_files/   pipeline outputs (git-ignored)
#     └── test_generator/    this package — config.py lives here
#
# Everything resolves relative to this file, so a fresh clone just works. If your
# machine puts these elsewhere, override per-location via environment variables:
#   TG_PDFBOX_DIR  -> the pdfbox *module* dir (where tests compile/run)
#   TG_INPUTS_DIR  -> dir holding extracted_metadata_final.json / call_graph.json
#   TG_OUTPUT_DIR  -> where generated_files/ output is written

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))          # .../test_generator
REPO_ROOT  = os.path.abspath(os.path.join(CONFIG_DIR, os.pardir)) # repo root (one up)

INPUTS_DIR = os.environ.get('TG_INPUTS_DIR', os.path.join(REPO_ROOT, 'inputs'))
PDFBOX_DIR = os.environ.get('TG_PDFBOX_DIR', os.path.join(REPO_ROOT, 'pdfbox', 'pdfbox'))
OUTPUT_DIR = os.environ.get('TG_OUTPUT_DIR', os.path.join(REPO_ROOT, 'generated_files'))
# Kept for the config_testable* variants that reference config.BASE_DIR.
BASE_DIR   = OUTPUT_DIR

GENRATED_FILES = os.path.join(OUTPUT_DIR, 'gemini_3.1pro_v7')
GENERATED_TESTS_DIR = os.path.join(PDFBOX_DIR, 'generated_tests_gemini_3.1pro_v7')
PROMPTS_DIR         = os.path.join(GENRATED_FILES, 'prompts')
RESPONSES_DIR       = os.path.join(GENRATED_FILES, 'responses')
PLANS_DIR           = os.path.join(GENRATED_FILES, 'plans')
RESULTS_DIR         = os.path.join(GENRATED_FILES, 'results')
RESULTS_JSON        = os.path.join(RESULTS_DIR, 'results.json')
FINAL_REPORT        = os.path.join(RESULTS_DIR, 'final_report.txt')
# Cumulative token-usage / cost totals, accumulated across every run.
USAGE_JSON          = os.path.join(RESULTS_DIR, 'usage.json')
INPUT_JSON          = os.path.join(INPUTS_DIR, 'extracted_metadata_final.json')
TEST_RESOURCES_DIR  = os.path.join(PDFBOX_DIR, 'src', 'test', 'resources')

# ============================================
# METHOD SELECTION
# ============================================
# When True, the pipeline processes ALL 1309 methods (including the 377 that
# already have developer tests). When False, only the 932 uncovered methods run
# (original behavior). For the 377 developer-tested methods to receive proper
# "HOW TO CONSTRUCT EACH INPUT" context, dependency_chains.json must be built
# with UNCOVERED_ONLY = False in build_dependency_chains.py.
INCLUDE_DEVELOPER_TESTED = True

# dependency_chains.json + class_inventory.json ship alongside this config.py
# (committed with test_generator/). call_graph.json lives in inputs/.
GENERATOR_DIR          = CONFIG_DIR
DEPENDENCY_CHAINS_FILE = os.path.join(GENERATOR_DIR, 'dependency_chains.json')
CLASS_INVENTORY_FILE   = os.path.join(GENERATOR_DIR, 'class_inventory.json')
CALL_GRAPH_FILE        = os.path.join(INPUTS_DIR, 'call_graph.json')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ============================================
# LLM SETTINGS
# ============================================
# Provider selects which API key + endpoint llm_client.py uses:
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
GCP_PROJECT     = os.environ.get('TG_GCP_PROJECT', 'your-gcp-project-id')
GCP_LOCATION    = os.environ.get('TG_GCP_LOCATION', 'global')
# OpenAI-compatible base URL for the 'gemini' provider only. For 'vertex' the URL
# is derived from GCP_PROJECT/GCP_LOCATION; for native OpenAI set to None.
LLM_BASE_URL    = 'https://generativelanguage.googleapis.com/v1beta/openai/'
LLM_MAX_TOKENS  = 16384
# NOTE: gpt-5* reasoning models only accept the default temperature, so this is
# ignored for them (see src/llm_client.py). It still applies to non-reasoning models.
LLM_TEMPERATURE = 0
# Reasoning effort: 'low' | 'medium' | 'high'. Applied to both Gemini (thinking
# level) and OpenAI gpt-5/o-series. Lower = fewer thinking tokens = lower cost.
LLM_REASONING_EFFORT = 'low'
API_SLEEP_SEC   = 1
MAX_RETRIES = 2

# ============================================
# TOKEN COST TRACKING
# ============================================
# USD price per 1,000,000 tokens for LLM_MODEL. Used only to compute the dollar
# figures in the progress summaries and final_report.txt — they do not affect
# generation.
# Verified for gemini-3.1-pro-preview (Jun 2026), standard tier, prompts <=200K
# tokens. Caveats not modeled here: prompts >200K tokens cost ~2x input / ~1.5x
# output, and the Batch API is half price ($1.00 / $6.00).
LLM_INPUT_COST_PER_1M  = 2.00   # prompt / input tokens
LLM_OUTPUT_COST_PER_1M = 12.00  # completion + reasoning (output) tokens
# ============================================
# MAVEN SETTINGS
# ============================================
TEST_TIMEOUT  = 30
MAVEN_TIMEOUT = 60
# Machine-specific tool locations (can't be project-relative). Each prefers an
# environment variable so collaborators don't edit this file:
#   - Leave MAVEN_EXECUTABLE empty ('') if 'mvn' is on PATH; the runner will find
#     it (it also checks MAVEN_HOME/M2_HOME). Otherwise set TG_MAVEN_EXECUTABLE
#     (or edit the fallback) to the full path of mvn / mvn.cmd.
#   - JAVA_HOME prefers your shell's JAVA_HOME; the fallback is only used if unset.
MAVEN_EXECUTABLE = os.environ.get(
    'TG_MAVEN_EXECUTABLE',
    r'C:\Program Files\maven\apache-maven-3.9.14-bin\apache-maven-3.9.14\bin\mvn.cmd')
JAVA_HOME = os.environ.get('JAVA_HOME', r'C:\Program Files\Java\ms-25.0.2')