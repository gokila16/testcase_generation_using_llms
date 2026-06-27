# Zero-Shot Test Generation (PDFBox)

A minimal lower-bound baseline for LLM test generation on [Apache PDFBox](https://pdfbox.apache.org/).
**Single shot, no context, no repair.**

For each public method in the target codebase, the pipeline:

1. Builds a zero-shot prompt from the method alone (class, signature, body, optional Javadoc).
2. Asks the LLM once for a JUnit 5 test class.
3. Compiles and runs the test against the bundled PDFBox module.
4. Records the outcome (PASSED / FAILED / COMPILE_FAILED / API_ERROR / EXTRACTION_FAILED).

There is no static-analysis context and no repair loop: the first response is taken as-is and
measured. This is the deliberate floor against which richer prompts are compared.

## Repository layout

```
.
├── pdfbox/                 Apache PDFBox 3.0.5 source (the system under test; bundled)
├── inputs/                 Precomputed method metadata consumed by the pipeline
├── test_generator/         The pipeline
│   ├── config.py           Settings + repo-relative paths
│   ├── pipeline_zeroshot.py  Entry point
│   └── src/                LLM client, prompt builder, Maven runner, reporting, ...
├── generated_files/        Pipeline outputs — created at run time (git-ignored)
├── requirements.txt
└── .env.example
```

> **Note on inputs.** `inputs/extracted_metadata_final.json` is shipped precomputed. It is produced
> by an upstream extraction step (SciTools Understand) that is **not** part of this repository.
> You do not need it to run the pipeline.

## Prerequisites

- Python 3.10+
- JDK 17+ and Apache Maven 3.9+ (for compiling and running the generated tests)
- An API key (or Google Cloud access) for the model you want to run — see below

## Supported models

The pipeline can run against any one of the following, selected with the `USE_*` flags
at the top of `test_generator/config.py` (set **exactly one** to `True`):

| Flag | Model | Access |
|------|-------|--------|
| `USE_DEEPSEEK_4_PRO`   | `deepseek-v4-pro`   | DeepSeek API (`DEEPSEEK_API_KEY`) |
| `USE_DEEPSEEK_4_FLASH` | `deepseek-v4-flash` | DeepSeek API (`DEEPSEEK_API_KEY`) |
| `USE_GPT_5_MINI`       | `gpt-5-mini`        | OpenAI API (`OPENAI_API_KEY`) |
| `USE_GPT_5_5`          | `gpt-5.5`           | OpenAI API (`OPENAI_API_KEY`) |
| `USE_GEMINI_3_5_FLASH` | `gemini-3.5-flash`  | Google Vertex AI (gcloud auth) |
| `USE_GEMINI_3_1_PRO`   | `gemini-3.1-pro`    | Google Vertex AI (gcloud auth) |

Outputs are namespaced per model, so switching models never overwrites a previous run's
results (e.g. `generated_files/zeroshot/deepseek-v4-pro/`).

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # then fill in the key(s) for your chosen model
```

Add the relevant credential to `.env`:

- **DeepSeek** → `DEEPSEEK_API_KEY`
- **OpenAI** → `OPENAI_API_KEY`
- **Gemini (Vertex AI)** → set `GOOGLE_CLOUD_PROJECT`, then authenticate once with
  Application Default Credentials:
  ```bash
  gcloud auth application-default login
  gcloud config set project <your-project>
  ```

If Maven or the JDK are not on your `PATH`, set `MAVEN_EXECUTABLE` and `JAVA_HOME` in `.env`.

## Run

```bash
cd test_generator
python pipeline_zeroshot.py
```

The run is resumable — methods already recorded in
`generated_files/zeroshot/<model>/results/results.json` are skipped. Generated tests, prompts,
responses and the final report are written under `generated_files/zeroshot/<model>/`.

## Configuration

All settings live in `test_generator/config.py`: model selection flags, the model registry
(provider, exact model id, reasoning/thinking effort), token budget, temperature, and Maven/JDK
timeouts. Secrets and machine-specific tool paths come from `.env`.
