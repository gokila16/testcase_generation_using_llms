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
# --- WICKET PORT -------------------------------------------------------------
# Retargeted to Apache Wicket 10.9.1. System under test is wicket-core, but
# generated WicketTester tests COMPILE & RUN in wicket-core-tests (wicket-core
# does not depend on wicket-tester; wicket-core-tests does). So PDFBOX_DIR points
# at wicket-core-tests. Set WICKET_MODULE_DIR in .env (machine-specific);
# fallback is the bundled trimmed reactor. Variable names kept as PDFBOX_* so
# maven_runner.py / file_manager.py need no edits.
#
# NOTE (v1 limitation): v1 reads only extracted_metadata_final.json and has no
# per-method construction context, so it does NOT receive the explicit
# WicketTester setup recipes (those live in dependency_chains.json, used by v7).
# v1 only sees WicketTester/FormTester/TagTester listed in source_file_imports;
# it must infer the harness usage. Expect weaker component-test quality than v7.
#
# Prereq: install wicket deps once so wicket-core-tests resolves them:
#   cd wicket && mvn install -Dmaven.test.skip=true -Dmaven.javadoc.skip=true \
#       -pl wicket-tester -am
_WICKET_MODULE = os.getenv("WICKET_MODULE_DIR") or os.path.join(
    REPO_ROOT, "wicket", "wicket-core-tests")
PDFBOX_DIR  = _WICKET_MODULE                      # wicket-core-tests (tests run here)
PDFBOX_REPO = os.path.dirname(_WICKET_MODULE)     # bundled wicket reactor root
# -----------------------------------------------------------------------------
INPUTS_DIR  = os.path.join(REPO_ROOT, 'inputs')          # Wicket precomputed inputs (Understand-derived)

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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # unused now; kept for parity

# ============================================
# LLM SETTINGS  (DeepSeek — OpenAI-compatible API)
# ============================================
# This v1 pipeline targets DeepSeek via its OpenAI-compatible endpoint. The
# OpenAI SDK is reused (src/llm_client.py) with only api_key + base_url changed.
DEEPSEEK_API_KEY  = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

LLM_MODEL       = 'deepseek-chat'   # DeepSeek's latest non-reasoning chat model
LLM_MAX_TOKENS  = 16384
# deepseek-chat is a standard (non-reasoning) model, so this temperature applies.
LLM_TEMPERATURE = 0
# Only used by reasoning models (e.g. OpenAI gpt-5/o-series). Ignored for
# deepseek-chat; kept so the model can be swapped without code changes.
LLM_REASONING_EFFORT = 'low'
API_SLEEP_SEC   = 1

# --- Token pricing (USD per 1,000,000 tokens) for the cost metric in the final
# report. VERIFY against current DeepSeek pricing — these are deepseek-chat list
# prices and may be out of date / not reflect off-peak discounts:
#   https://api-docs.deepseek.com/quick_start/pricing
# DeepSeek bills cached input tokens (cache HIT) cheaper than fresh input (MISS).
PRICE_INPUT_CACHE_MISS_PER_1M = 0.27   # fresh prompt tokens
PRICE_INPUT_CACHE_HIT_PER_1M  = 0.07   # cached prompt tokens
PRICE_OUTPUT_PER_1M           = 1.10   # completion tokens
MAX_RETRIES = 2

# ============================================
# MAVEN / JDK SETTINGS
# ============================================
# IMPORTANT (Wicket): maven_runner compiles the WHOLE wicket-core-tests test
# source set each call (~1160 files). A WARM incremental testCompile measured ~27s
# on this machine; a COLD full compile is much longer. The old pdfbox defaults
# (30/60s) caused EVERY method to time out -> false COMPILE_FAILED. These are
# raised with headroom. Keep the target module pre-built (warm) so compiles stay
# incremental — point WICKET_MODULE_DIR at a checkout whose target/test-classes
# already exists.
TEST_TIMEOUT  = 120   # per generated-test surefire run (WicketTester startup + 1 test)
MAVEN_TIMEOUT = 240   # per compile (full test source set; generous for cold compiles)
# Read tool locations from the environment so each machine provides its own.
# Leave them unset (in .env) to let the pipeline use 'mvn' from PATH and the
# system JAVA_HOME. Set them only if Maven / the JDK are not on PATH.
#   e.g. MAVEN_EXECUTABLE=C:\Program Files\apache-maven-3.9.x\bin\mvn.cmd
#   e.g. JAVA_HOME=C:\Program Files\Java\jdk-21
MAVEN_EXECUTABLE = os.getenv("MAVEN_EXECUTABLE")
JAVA_HOME        = os.getenv("JAVA_HOME")
