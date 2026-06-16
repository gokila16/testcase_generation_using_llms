# Test Case Generation using LLMs — v7 (SAGE)

Automated generation of JUnit unit tests for [Apache PDFBox](https://pdfbox.apache.org/)
using a Large Language Model. This is the **v7 / SAGE** pipeline: a multi-stage
**plan → generate → static-check → compile/run → repair** loop driven by
Anthropic Claude.

For each public method in the target codebase, the pipeline:

1. **Plans** the test from the method's metadata, its dependency chain, caller
   snippets, and a control-flow slice of the method body.
2. **Generates** a JUnit test from that plan.
3. **Statically checks** the test against an allowlist of real method/import
   signatures (`class_inventory.json`) to catch hallucinated APIs *before* compiling.
4. **Compiles and runs** the test against the bundled PDFBox module.
5. **Repairs** failures by feeding the compiler/test error back to the model,
   retrying up to a configurable number of times.
6. Records the outcome (passed / failed / compile-failed / allowlist-failed / error)
   for every method.

## Repository layout

```
.
├── pdfbox/                 Apache PDFBox source (the system under test; bundled)
├── inputs/                 Precomputed inputs consumed by the pipeline:
│   ├── extracted_metadata_final.json   method metadata
│   ├── dependency_chains.json          per-method dependency chains
│   ├── call_graph.json                 caller snippets
│   └── class_inventory.json            allowlist of real classes/methods
├── test_generator/         The pipeline
│   ├── config.py           All settings + repo-relative paths
│   ├── pipeline_step3.py    Entry point: the plan/generate/check/repair loop
│   ├── run_generated_tests.py  Re-run previously generated tests
│   └── src/                LLM client, prompt builder, allowlist checker,
│                           CFG slicer, Java post-processor, Maven runner, ...
├── generated_files/        Pipeline outputs — created at run time (git-ignored)
├── requirements.txt
└── .env.example
```

> **Note on inputs.** The files in `inputs/` are shipped precomputed. They are
> produced by an upstream extraction/analysis stage that depends on the commercial
> *SciTools Understand* tool, which is **not** part of this repository. You do not
> need it to run the pipeline.

## Branches

- **`SAGE-v7`** — this pipeline.
- **`prompt-and-repair`** — the simpler v1 pipeline (gpt-5-mini).
- **`main`** — shared base: the PDFBox source and the common method metadata.

## Prerequisites

- **Python** 3.10+
- **JDK** capable of building PDFBox (Java 11+; developed with a Java 25 build)
- **Apache Maven** 3.9.x
- An **Anthropic API key**

Maven and the JDK must be on your `PATH`, or their locations set in `.env`.

## Setup

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env          # on Windows: copy .env.example .env
#   then edit .env and set ANTHROPIC_API_KEY (and MAVEN_EXECUTABLE / JAVA_HOME if needed)

# 3. Install the bundled PDFBox modules into your local Maven repository (one time).
#    PDFBox here is 4.0.0-SNAPSHOT, so its sibling modules (io, fontbox, xmpbox, ...)
#    are NOT on Maven Central and must be built locally first, or test compilation
#    will fail to resolve them.
cd pdfbox
mvn install -DskipTests
cd ..
```

## Running

```bash
cd test_generator
python pipeline_step3.py
```

Useful flags:

- `--only <full_name>` — run a single method end-to-end (ignores existing results).
  Recommended for a first smoke check.
- `--skip-file <path.json>` — re-run everything except the unique_keys listed in the
  file (used to protect an already-passing baseline).

The pipeline skips methods that already have a result, so it is safe to stop and resume.

## Output

All output is written under `generated_files/v7/` (git-ignored):

- `plans/`     — the per-method test plan
- `prompts/`   — every prompt sent to the model
- `responses/` — every raw model response
- `results/results.json` — per-method outcome
- `results/final_report.txt` — summary report

Generated test files are written into the PDFBox module under
`pdfbox/pdfbox/generated_tests/` while compiling/running.

## Configuration

Key settings live in `test_generator/config.py`:

| Setting | Meaning |
| --- | --- |
| `LLM_MODEL` | Model id (default `claude-sonnet-4-6`) |
| `LLM_MAX_TOKENS` | Max output tokens per call |
| `MAX_RETRIES` | Compile/run repair attempts per method |
| `INCLUDE_DEVELOPER_TESTED` | Process all methods, or only uncovered ones |
| `TEST_TIMEOUT`, `MAVEN_TIMEOUT` | Per-test / per-build timeouts (seconds) |
