import os
from dotenv import load_dotenv

# ============================================
# REPO ANCHOR
# ============================================
# Everything is resolved relative to the repository root so this pipeline runs on
# any machine without editing paths. This file lives in <repo>/test_generator/,
# so the repo root is one directory up.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(_THIS_DIR)

# Load environment variables (API key, optional tool paths) from <repo>/.env
load_dotenv(os.path.join(REPO_ROOT, '.env'))

# ============================================
# PATHS
# ============================================
PDFBOX_REPO = os.path.join(REPO_ROOT, 'pdfbox')          # multi-module Maven repo root (bundled)
PDFBOX_DIR  = os.path.join(PDFBOX_REPO, 'pdfbox')        # the actual pdfbox Maven module
INPUTS_DIR  = os.path.join(REPO_ROOT, 'inputs')          # bundled precomputed inputs

# Repo-local output location (git-ignored, regenerated on every run)
GENRATED_FILES      = os.path.join(REPO_ROOT, 'generated_files', 'v1')
GENERATED_TESTS_DIR = os.path.join(PDFBOX_DIR, 'generated_testsgpt5mini_v1')
PROMPTS_DIR         = os.path.join(GENRATED_FILES, 'prompts')
RESPONSES_DIR       = os.path.join(GENRATED_FILES, 'responses')
RESULTS_DIR         = os.path.join(GENRATED_FILES, 'results')
RESULTS_JSON        = os.path.join(RESULTS_DIR, 'results.json')
FINAL_REPORT        = os.path.join(RESULTS_DIR, 'final_report.txt')

# Precomputed method metadata (shipped in inputs/). Produced upstream by the
# Understand-based extraction step, which is NOT part of this runnable repo.
INPUT_JSON          = os.path.join(INPUTS_DIR, 'extracted_metadata_final.json')

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ============================================
# LLM SETTINGS
# ============================================
LLM_MODEL       = 'gpt-5-mini'
# gpt-5 / o-series are reasoning models: this budget is shared by hidden reasoning
# tokens AND the visible output, so keep it generous (sent as max_completion_tokens).
LLM_MAX_TOKENS  = 16384
# Reasoning models only allow the default temperature, so this is IGNORED for gpt-5
# (handled in src/llm_client.py). Kept for non-reasoning fallback models.
LLM_TEMPERATURE = 0
# gpt-5 reasoning effort: 'minimal' | 'low' | 'medium' | 'high'.
LLM_REASONING_EFFORT = 'low'
API_SLEEP_SEC   = 1
MAX_RETRIES = 2

# ============================================
# MAVEN / JDK SETTINGS
# ============================================
TEST_TIMEOUT  = 30
MAVEN_TIMEOUT = 60
# Read tool locations from the environment so each machine provides its own.
# Leave them unset (in .env) to let the pipeline use 'mvn' from PATH and the
# system JAVA_HOME. Set them only if Maven / the JDK are not on PATH.
#   e.g. MAVEN_EXECUTABLE=C:\Program Files\apache-maven-3.9.x\bin\mvn.cmd
#   e.g. JAVA_HOME=C:\Program Files\Java\jdk-21
MAVEN_EXECUTABLE = os.getenv("MAVEN_EXECUTABLE")
JAVA_HOME        = os.getenv("JAVA_HOME")
