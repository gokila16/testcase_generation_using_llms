# Test Case Generation using LLMs

Automated generation of JUnit unit tests for [Apache PDFBox](https://pdfbox.apache.org/)
using a Large Language Model with an iterative **prompt-and-repair** loop.

> This is the **`v1_gemini`** branch: the v1 pipeline running on **Google Vertex AI**
> (Gemini 3.1 Pro). Authentication is via gcloud Application Default Credentials —
> there is no API key to copy. See [Branches](#branches) for other variants.

For each public method in the target codebase, the pipeline:

1. Builds a prompt from the method's metadata (signature, Javadoc, body, usage snippets).
2. Asks the LLM to generate a JUnit test.
3. Compiles and runs the test against the bundled PDFBox module.
4. If compilation or the test fails, feeds the error back to the LLM and **repairs**
   the test — retrying up to a configurable number of times.
5. Records the outcome (passed / failed / compile-failed / error) for every method.

## Repository layout

```
.
├── pdfbox/                 Apache PDFBox source (the system under test; bundled)
├── inputs/                 Precomputed method metadata consumed by the pipeline
├── test_generator/         The pipeline
│   ├── config.py           All settings + repo-relative paths
│   ├── pipeline_step3.py    Entry point: the prompt-and-repair generation loop
│   ├── smoke_test.py       Minimal end-to-end check (one method)
│   └── src/                LLM client, prompt builder, Maven runner, reporting, ...
├── generated_files/        Pipeline outputs — created at run time (git-ignored)
├── requirements.txt
└── .env.example
```

> **Note on inputs.** `inputs/extracted_metadata_final.json` is shipped precomputed.
> It is produced by an upstream extraction step that depends on the commercial
> *SciTools Understand* tool, which is **not** part of this repository. You do not
> need it to run the pipeline.

## Branches

- **`v1_gemini`** — this branch: the v1 pipeline on Vertex AI (Gemini 3.1 Pro).
- **`v7_gemini`** — the v7 pipeline on Vertex AI (Gemini 3.1 Pro).
- **`prompt-and-repair`** — the original v1 pipeline (gpt-5-mini, native OpenAI).
- (`main` holds the shared PDFBox source and inputs; pipeline variants branch from it.)

## Prerequisites

- **Python** 3.10+
- **JDK** capable of building PDFBox (Java 11+; developed with a Java 25 build)
- **Apache Maven** 3.9.x
- **Google Cloud CLI** (`gcloud`) and a GCP project with billing enabled, the
  **Vertex AI API** enabled, and your account granted the **Vertex AI User** role

Maven and the JDK must be on your `PATH`, or their locations set in `.env` (see below).

## Setup

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Authenticate to Vertex AI (opens a browser; no API key to copy)
gcloud auth application-default login
#   then set TG_GCP_PROJECT in .env, or edit GCP_PROJECT in test_generator/config.py

# 3. Configure environment
cp .env.example .env          # on Windows: copy .env.example .env
#   edit .env: set TG_GCP_PROJECT (and TG_MAVEN_EXECUTABLE / JAVA_HOME if needed)

# 4. Install the bundled PDFBox modules into your local Maven repository (one time).
#    PDFBox's sibling modules (io, fontbox, xmpbox, ...) are NOT on Maven Central
#    and must be built locally first, or test compilation will fail to resolve them.
cd pdfbox
mvn install -DskipTests
cd ..
```

## Running

```bash
cd test_generator
python pipeline_step3.py
```

The pipeline skips methods that already have a result, so it is safe to stop and
resume. To verify your setup end-to-end on a single method first:

```bash
cd test_generator
python smoke_test.py
```

## Output

All output is written under `generated_files/gemini_3.1pro_v1/` (git-ignored):

- `prompts/`   — every prompt sent to the LLM
- `responses/` — every raw LLM response
- `results/results.json` — per-method outcome
- `results/final_report.txt` — summary report

Generated test files are written into the PDFBox module under
`pdfbox/pdfbox/generated_tests_gemini_3.1pro_v1/` while compiling/running.

## Configuration

Key settings live in `test_generator/config.py`:

| Setting | Meaning |
| --- | --- |
| `LLM_PROVIDER` | `vertex` (default) / `gemini` / `openai` |
| `LLM_MODEL` | Model id (default `gemini-3.1-pro-preview`) |
| `GCP_PROJECT`, `GCP_LOCATION` | Vertex AI project + region (`global` for Gemini 3.x preview) |
| `LLM_MAX_TOKENS` | Max tokens in the model response |
| `LLM_REASONING_EFFORT` | `low` / `medium` / `high` — Gemini thinking budget |
| `MAX_RETRIES` | Repair attempts per method |
| `TEST_TIMEOUT`, `MAVEN_TIMEOUT` | Per-test / per-build timeouts (seconds) |
