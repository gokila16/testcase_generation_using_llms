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
OUTPUT_DIR          = os.path.join(REPO_ROOT, 'generated_files', 'v7')
GENERATED_TESTS_DIR = os.path.join(PDFBOX_DIR, 'generated_tests')
PROMPTS_DIR         = os.path.join(OUTPUT_DIR, 'prompts')
RESPONSES_DIR       = os.path.join(OUTPUT_DIR, 'responses')
PLANS_DIR           = os.path.join(OUTPUT_DIR, 'plans')
RESULTS_DIR         = os.path.join(OUTPUT_DIR, 'results')
RESULTS_JSON        = os.path.join(RESULTS_DIR, 'results.json')
FINAL_REPORT        = os.path.join(RESULTS_DIR, 'final_report.txt')

# Precomputed inputs (shipped in inputs/). Produced upstream by the Understand-based
# extraction + analysis steps, which are NOT part of this runnable repo.
INPUT_JSON          = os.path.join(INPUTS_DIR, 'extracted_metadata_final.json')
TEST_RESOURCES_DIR  = os.path.join(PDFBOX_DIR, 'src', 'test', 'resources')

# ============================================
# METHOD SELECTION
# ============================================
# When True, the pipeline processes ALL methods (including those that already have
# developer tests). When False, only uncovered methods run.
INCLUDE_DEVELOPER_TESTED = True

DEPENDENCY_CHAINS_FILE = os.path.join(INPUTS_DIR, 'dependency_chains.json')
CALL_GRAPH_FILE        = os.path.join(INPUTS_DIR, 'call_graph.json')
CLASS_INVENTORY_FILE   = os.path.join(INPUTS_DIR, 'class_inventory.json')

OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")     # unused by this pipeline; kept for parity
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# ============================================
# LLM SETTINGS
# ============================================
LLM_MODEL       = 'claude-sonnet-4-6'
LLM_MAX_TOKENS  = 16384
LLM_TEMPERATURE = 0
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
