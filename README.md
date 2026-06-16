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

## Changing the model

This pipeline talks to Anthropic Claude through `test_generator/src/llm_client.py`.

**To use a different Claude model — no code changes:**

- Edit `LLM_MODEL` in `test_generator/config.py`. Examples:
  - `claude-opus-4-8` — most capable
  - `claude-sonnet-4-6` — default (balanced)
  - `claude-haiku-4-5-20251001` — fastest / cheapest
- `ANTHROPIC_API_KEY` is unchanged. `LLM_MAX_TOKENS` and `LLM_TEMPERATURE` still apply.

**To switch to a different vendor** (OpenAI, Google, DeepSeek, …):

Three steps: **(1)** replace `src/llm_client.py` with one that calls the new SDK but
keeps the **exact same contract**, since `pipeline_step3.py` depends on it:

> `call_llm(prompt, method_name=None, system=None)` must return a
> **`(text: str | None, was_truncated: bool)` tuple**. `system` is a static
> instruction block — map it to the new vendor's system message. `was_truncated`
> just lets the pipeline count truncations; set it from the vendor's
> length/max-token finish reason (the Anthropic original additionally requests a
> continuation, which is optional and can be dropped for other vendors).

**(2)** update `requirements.txt` (remove `anthropic` if unused); **(3)** set the new
key in `.env` and reference it in `config.py`.

Drop-in `src/llm_client.py` for each vendor:

<details><summary><b>OpenAI (GPT)</b></summary>

```python
import time
from openai import OpenAI
import config

client = OpenAI(api_key=config.OPENAI_API_KEY)

def _is_reasoning(model):
    m = (model or '').lower()
    return any(m.startswith(p) for p in ('gpt-5', 'o1', 'o3', 'o4'))

def call_llm(prompt, method_name=None, system=None):
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    kwargs = {"model": config.LLM_MODEL, "messages": messages}
    if _is_reasoning(config.LLM_MODEL):
        kwargs["max_completion_tokens"] = config.LLM_MAX_TOKENS      # reasoning models
    else:
        kwargs["max_tokens"]  = config.LLM_MAX_TOKENS                # standard models
        kwargs["temperature"] = config.LLM_TEMPERATURE
    try:
        resp = client.chat.completions.create(**kwargs)
        time.sleep(config.API_SLEEP_SEC)
        choice = resp.choices[0]
        return choice.message.content, (choice.finish_reason == "length")
    except Exception as e:
        print(f"  API Error: {type(e).__name__}: {e}")
        return None, False
```
- `requirements.txt`: `openai`
- `config.py`: `OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")`; `LLM_MODEL = 'gpt-5-mini'`
- `.env`: `OPENAI_API_KEY=...`
</details>

<details><summary><b>Google (Gemini)</b></summary>

```python
import time
import google.generativeai as genai           # SDK: google-generativeai (legacy)
import config

genai.configure(api_key=config.GEMINI_API_KEY)

def call_llm(prompt, method_name=None, system=None):
    try:
        model = genai.GenerativeModel(config.LLM_MODEL,            # e.g. 'gemini-2.5-pro'
                                      system_instruction=(system or None))
        resp = model.generate_content(
            prompt,
            generation_config={"temperature": config.LLM_TEMPERATURE,
                               "max_output_tokens": config.LLM_MAX_TOKENS},
        )
        time.sleep(config.API_SLEEP_SEC)
        finish = resp.candidates[0].finish_reason if resp.candidates else None
        return (resp.text or None), str(finish).endswith("MAX_TOKENS")
    except Exception as e:
        print(f"  API Error: {type(e).__name__}: {e}")
        return None, False
```
- `requirements.txt`: `google-generativeai`  (the newer `google-genai` SDK uses a different call style — adjust if you use it)
- `config.py`: `GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")`; `LLM_MODEL = 'gemini-2.5-pro'`
- `.env`: `GEMINI_API_KEY=...`
</details>

<details><summary><b>DeepSeek (OpenAI-compatible — easiest)</b></summary>

DeepSeek serves an OpenAI-compatible API. Use the **OpenAI drop-in above** with one
change to the client line, and keep `_is_reasoning` returning `False` for it:

```python
client = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
```
- keep `openai` in `requirements.txt`
- `config.py`: `DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")`; `LLM_MODEL = 'deepseek-chat'`
- `.env`: `DEEPSEEK_API_KEY=...`
</details>
