# RQ3 — V7 Leave-One-Out Ablation Study (Apache PDFBox 3.0.5)

This branch quantifies how much each component of the **V7** test-generation
pipeline contributes, using a **leave-one-out (LOO)** ablation: run the full
pipeline with every component on (`baseline`), then re-run it with exactly **one
component removed at a time**, over the same 1309 PDFBox methods, and compare the
outcome distributions.

The generator builds a prompt for each public method, asks **Gemini
(`gemini-3.5-flash`, via Vertex AI, temperature 0)** for a JUnit test, validates it
against an allowlist, compiles & runs it with Maven against the bundled PDFBox
module, repairs on failure, and records a terminal outcome. Each ablation switches
off one of those components.

The system under test is **Apache PDFBox 3.0.5**, bundled in this repo at
[`pdfbox/`](pdfbox/) so generated tests compile and run without an external checkout.

## The seven ablated components

| `ABLATION_LABEL` | Flag set to `False` | What is removed |
| --- | --- | --- |
| `baseline`    | *(none)*    | nothing — all components on |
| `no_slicing`  | `slicing`   | CFG behavioral-slice guidance |
| `no_chains`   | `chains`    | "HOW TO CONSTRUCT EACH INPUT" construction recipes |
| `no_callers`  | `callers`   | "REAL USAGE EXAMPLES" call-site snippets |
| `no_allowlist`| `allowlist` | import + method-call hallucination gate (and its correction retries) |
| `no_facts`    | `facts`     | "PRE-COMPUTED BEHAVIORAL FACTS" section (branch map / throw contracts / literal returns) |
| `no_repair`   | `repair`    | Maven compile/runtime retry loop (`MAX_RETRIES` → 0) |
| `no_planning` | `planning`  | two-step plan→generate split — collapses to one-shot generation (same context & reasoning, single LLM call) |

`7 ablations + baseline = 8 runs.`

See [`ABLATION_SPEC.md`](ABLATION_SPEC.md) for the design and exact toggle points,
and [`ABLATION_RUNBOOK.txt`](ABLATION_RUNBOOK.txt) for the original operator runbook.

## Repository layout

```
.
├── pdfbox/                  Apache PDFBox 3.0.5 reactor (system under test; bundled)
├── inputs/                  Precomputed, read-only inputs (same for every condition)
│   ├── extracted_metadata_final.json   1309 methods + metadata
│   ├── dependency_chains.json          per-method construction recipes (chains)
│   ├── class_inventory.json            class structure for instantiation
│   └── call_graph.json                 caller snippets (real usage examples)
├── test_generator/          The pipeline
│   ├── config.py            All settings + the ABLATION switch + repo-relative paths
│   ├── pipeline_step3.py    Entry point: generate → validate → compile → run → repair
│   └── src/                 LLM client, prompt builder, Maven runner, allowlist, ...
├── generated_files/         Outputs — created per run, git-ignored
├── requirements.txt
└── .env.example
```

> **On the inputs.** The four `inputs/` files are shipped precomputed. They are
> produced by an upstream extraction step that depends on the commercial
> *SciTools Understand* tool, which is **not** part of this repo and is **not**
> needed to run the ablation. They are identical across all conditions — the
> ablation removes context **in code**, never by editing these files, so do not
> regenerate them between runs. (`test_generator/build_*.py` are provenance only.)

## Prerequisites

- **Python** 3.10+
- **JDK** capable of building PDFBox 3.0.5 (Java 11+)
- **Apache Maven** 3.9.x
- A **Google Cloud project** with the **Vertex AI API** enabled, and the
  [`gcloud` CLI](https://cloud.google.com/sdk/docs/install) for authentication.

Maven and the JDK must be on your `PATH`, or set in `.env` (see below).

## Setup

```bash
# 1. Python dependencies
pip install -r requirements.txt

# 2. Authenticate to Vertex AI (Application Default Credentials), one time:
gcloud auth application-default login
gcloud config set project <your-gcp-project>

# 3. Configure environment
cp .env.example .env          # Windows: copy .env.example .env
#   then edit .env and set VERTEX_PROJECT=<your-gcp-project>
#   (and MAVEN_EXECUTABLE / JAVA_HOME only if they are not on PATH)

# 4. Build/install the bundled PDFBox reactor into your local Maven repo (one time),
#    so the pdfbox module resolves its sibling modules when compiling generated tests:
cd pdfbox
mvn install -DskipTests
cd ..
```

## Running a condition

Each condition changes **two lines** in [`test_generator/config.py`](test_generator/config.py):

```python
ABLATION_LABEL = 'no_facts'          # 1. name the run
ABLATION = { ... 'facts': False ...} # 2. flip the ONE matching flag to False
```

> **The #1 footgun:** the label and the `False` flag must agree
> (`'no_facts'` ⇔ `'facts': False`). A mismatch silently produces a second
> baseline in a folder named after a different condition.

Then run the generator:

```bash
cd test_generator
python pipeline_step3.py
```

Results land in `generated_files/v7-loo-<label>/results/results.json`. The pipeline
skips methods that already have a recorded result, so a run is safe to stop and
resume. Run **one condition at a time** and let it finish — a full condition is 1309
methods × ~2–8 Gemini calls + a Maven compile/run each, so it is long.

To reproduce the whole study, run all seven labels:
`baseline, no_slicing, no_chains, no_callers, no_allowlist, no_facts, no_repair, no_planning`.

## Output & analysis

Per condition, under `generated_files/v7-loo-<label>/` (all git-ignored):

- `prompts/`, `plans/`, `responses/` — every prompt, plan, and raw Gemini response
- `results/results.json` — per-method terminal outcome
- `results/final_report.txt` — summary

Each method ends in one of: `PASSED, FAILED, COMPILE_FAILED, ALLOWLIST_FAILED,
ALLOWLIST_FAILED_ON_RETRY, EXTRACTION_FAILED, API_ERROR`.

Headline metric per condition is **pass rate = PASSED / 1309**; compare each
condition's pass rate and failure-mode shift against the baseline. Expected sanity
checks: `no_allowlist` → more `COMPILE_FAILED`; `no_repair` → more
`COMPILE_FAILED`/`FAILED`; `no_facts` → more `FAILED` (wrong oracles).

Generated test sources are written into the PDFBox module at
`pdfbox/pdfbox/generated_tests_v7-loo-<label>/` while compiling/running.

## Notes & gotchas

- **`VERTEX_LOCATION` must stay `global`** — Gemini 3.x is only served there.
- **ADC tokens expire.** On mid-run 401/403/"reauth" errors, re-run
  `gcloud auth application-default login`.
- **Quota / 429:** the client backs off 60s once on `RESOURCE_EXHAUSTED` then
  retries; sustained 429s mean you are over Vertex quota.
- **Determinism:** Gemini at `temperature=0` is near-deterministic but not
  bit-identical; treat small baseline-vs-baseline differences as noise, not a
  component effect.

## Branches

`main` holds the shared PDFBox source and base inputs. Pipeline variants branch
from it (e.g. `prompt-and-repair` is the gpt-5-mini v1 baseline); this
**`rq3-ablation`** branch is the V7 Gemini leave-one-out study.
