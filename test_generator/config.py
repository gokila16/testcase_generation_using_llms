import os
from dotenv import load_dotenv

# ============================================================
# REPO ANCHOR
# ============================================================
# Everything resolves relative to the repository root so this pipeline runs on
# any machine without editing paths. This file lives in <repo>/test_generator/,
# so the repo root is one directory up.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(_THIS_DIR)

# Load environment variables (Vertex project, optional tool paths) from <repo>/.env
load_dotenv(os.path.join(REPO_ROOT, '.env'))

# ============================================================
# PATHS  (RQ3 — V7 leave-one-out ablation on Apache PDFBox 3.0.5)
# ============================================================
# The system under test is the PDFBox 3.0.5 reactor bundled in this repo at
# <repo>/pdfbox. Generated tests COMPILE & RUN inside the `pdfbox` module
# (<repo>/pdfbox/pdfbox), which is where PDFBOX_DIR points. Point it elsewhere by
# setting PDFBOX_MODULE_DIR in .env (e.g. your own PDFBox 3.0.5 checkout).
PDFBOX_DIR = os.getenv("PDFBOX_MODULE_DIR") or os.path.join(REPO_ROOT, "pdfbox", "pdfbox")

# Precomputed inputs (Understand-derived), shipped in inputs/. These are the SAME
# read-only inputs for every condition — the ablation removes context in code, not
# by editing these files. Do not regenerate them between conditions.
INPUTS_DIR             = os.path.join(REPO_ROOT, 'inputs')
INPUT_JSON             = os.path.join(INPUTS_DIR, 'extracted_metadata_final.json')
DEPENDENCY_CHAINS_FILE = os.path.join(INPUTS_DIR, 'dependency_chains.json')
CLASS_INVENTORY_FILE   = os.path.join(INPUTS_DIR, 'class_inventory.json')
CALL_GRAPH_FILE        = os.path.join(INPUTS_DIR, 'call_graph.json')

# PDFBox test resources (PDFs/fonts the generated tests load), inside the module.
TEST_RESOURCES_DIR     = os.path.join(PDFBOX_DIR, 'src', 'test', 'resources')

# ============================================================
# RQ3 ABLATION SWITCH
# ============================================================
# One condition per run. Set ABLATION_LABEL to the condition name and flip the
# matching flag in ABLATION (below) to False. 'baseline' = all components on.
# Output dirs are keyed by this label so conditions never clobber each other.
#
# RULE: the label and the False flag must agree (label 'no_facts' <-> 'facts': False).
# This is manual on purpose so a run can never silently mislabel its output.
ABLATION_LABEL = 'baseline'

# Each flag True = component ENABLED. For a leave-one-out run, set exactly ONE to
# False and set ABLATION_LABEL to match (e.g. label 'no_facts' -> 'facts': False).
ABLATION = {
    'slicing':   True,   # cfg_slicer behavioral slices         -> [] (pipeline_step3)
    'chains':    True,   # dependency_chains construction recipe -> None (pipeline_step3)
    'callers':   True,   # real caller snippets                  -> [] (pipeline_step3)
    'allowlist': True,   # import + method-call hallucination gate (incl. its correction retries)
    'facts':     True,   # pre-computed behavioral facts section -> "" (prompt_builder)
    'repair':    True,   # Maven compile/runtime retry loop      -> MAX_RETRIES forced to 0
    # 'planning': True,  # deferred: needs a one-shot generation prompt builder
}

# ============================================================
# OUTPUT ISOLATION  (so runs never overwrite each other)
# ============================================================
# Repo-local outputs (git-ignored, regenerated on every run), keyed by label.
GENRATED_FILES      = os.path.join(REPO_ROOT, 'generated_files', f'v7-loo-{ABLATION_LABEL}')
# Test sources must live inside the PDFBox module so Maven can compile them.
GENERATED_TESTS_DIR = os.path.join(PDFBOX_DIR, f'generated_tests_v7-loo-{ABLATION_LABEL}')
PROMPTS_DIR         = os.path.join(GENRATED_FILES, 'prompts')
RESPONSES_DIR       = os.path.join(GENRATED_FILES, 'responses')
PLANS_DIR           = os.path.join(GENRATED_FILES, 'plans')
RESULTS_DIR         = os.path.join(GENRATED_FILES, 'results')
RESULTS_JSON        = os.path.join(RESULTS_DIR, 'results.json')
FINAL_REPORT        = os.path.join(RESULTS_DIR, 'final_report.txt')

# ============================================================
# METHOD SELECTION
# ============================================================
# True  -> process ALL 1309 methods (including the 377 with developer tests).
# False -> only the 932 uncovered methods. The shipped inputs were built for the
# full set, so keep this True to reproduce the study.
INCLUDE_DEVELOPER_TESTED = True

# ============================================================
# LLM SETTINGS  (Gemini via Vertex AI)
# ============================================================
# Auth uses Application Default Credentials. One-time per machine:
#   gcloud auth application-default login
#   gcloud config set project <your-gcp-project>
# Then set VERTEX_PROJECT in .env to your own GCP project id.
VERTEX_PROJECT  = os.getenv("VERTEX_PROJECT")             # REQUIRED — your GCP project
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "global")  # Gemini 3.x is served only on 'global'
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")             # only if you switch to the Gemini Developer API

LLM_MODEL       = 'gemini-3.5-flash'
LLM_MAX_TOKENS  = 16384
LLM_TEMPERATURE = 0
API_SLEEP_SEC   = 1
MAX_RETRIES     = 2

# ============================================================
# MAVEN / JDK SETTINGS
# ============================================================
TEST_TIMEOUT  = 30
MAVEN_TIMEOUT = 60
# Read tool locations from the environment so each machine provides its own.
# Leave unset (in .env) to use 'mvn' from PATH and the system JAVA_HOME. Set them
# only if Maven / the JDK are NOT on PATH:
#   MAVEN_EXECUTABLE=C:\Program Files\apache-maven-3.9.x\bin\mvn.cmd
#   JAVA_HOME=C:\Program Files\Java\jdk-21
MAVEN_EXECUTABLE = os.getenv("MAVEN_EXECUTABLE")
JAVA_HOME        = os.getenv("JAVA_HOME")
