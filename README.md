# Test Case Generation using LLMs — Wicket, v1

Automated generation of JUnit unit tests for [Apache Wicket](https://wicket.apache.org/)
**10.9.1** using a Large Language Model with an iterative **prompt-and-repair** loop.
This is the **v1** pipeline; the system under test is the `wicket-core` module.

For each public method in the target codebase, the pipeline:

1. Builds a prompt from the method's metadata (signature, Javadoc, body, usage snippets).
2. Asks the LLM to generate a JUnit test.
3. Compiles and runs the test in the `wicket-core-tests` module (WicketTester on classpath).
4. If compilation or the test fails, feeds the error back to the LLM and **repairs**
   the test — retrying up to a configurable number of times.
5. Records the outcome (passed / failed / compile-failed / error) for every method.

> **v1 vs v7 for Wicket.** v1 reads only `extracted_metadata_final.json` and has no
> per-method construction context, so it does **not** get the explicit WicketTester
> setup recipes that the **v7 (`wicketv7`)** branch injects via `dependency_chains.json`.
> v1 only sees `WicketTester`/`FormTester`/`TagTester` in the available imports and
> must infer the harness. For higher component-test quality, use the `wicketv7` branch.

## Repository layout

```
.
├── wicket/                 Apache Wicket 10.9.1 source — trimmed reactor (the
│                           system under test; bundled). Modules: wicket-util,
│                           wicket-request, wicket-core, wicket-tester,
│                           wicket-core-tests.
├── inputs/                 Precomputed method metadata consumed by the pipeline
│                           (v1 uses extracted_metadata_final.json; the other
│                           inputs are shipped for parity with v7).
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

- **`wicketv1`** — this pipeline (Wicket, v1 prompt-and-repair, DeepSeek `deepseek-chat`).
- **`wicketv7`** — the multi-stage v7 / SAGE pipeline for Wicket (with WicketTester recipes).
- **`avrov1` / `avrov7`** — the same two pipelines targeting Apache Avro.
- **`SAGE-v7` / `prompt-and-repair`** — the original PDFBox pipelines.

## Prerequisites

- **Python** 3.10+
- **JDK** capable of building Wicket 10 (Java 17+; verified with a Java 25 build)
- **Apache Maven** 3.9.x
- A **DeepSeek API key**

Maven and the JDK must be on your `PATH`, or their locations set in `.env` (see below).

## Setup

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env          # on Windows: copy .env.example .env
#   then edit .env and set DEEPSEEK_API_KEY (and MAVEN_EXECUTABLE / JAVA_HOME if needed)

# 3. Install the bundled Wicket modules into your local Maven repository (one time)
#    so wicket-core-tests can resolve wicket-core / wicket-tester. Skip javadoc:
#    JDK 25's doclint rejects old {@link} tags in a package.html.
cd wicket
mvn install -Dmaven.test.skip=true -Dmaven.javadoc.skip=true -pl wicket-tester -am
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

All output is written under `generated_files/v1/` (git-ignored):

- `prompts/`   — every prompt sent to the LLM
- `responses/` — every raw LLM response
- `results/results.json` — per-method outcome
- `results/final_report.txt` — summary report, including a **TOKEN USAGE & COST**
  section: API calls, prompt/completion/total tokens (with DeepSeek cache hit/miss
  split), estimated USD cost, and average cost per method. Prices come from the
  `PRICE_*` constants in `config.py` — **verify them against current DeepSeek
  pricing**, as list prices change.

Generated test files are written into the Wicket tests module under
`wicket/wicket-core-tests/generated_testsgpt5mini_v1/` while compiling/running, and
cleaned up afterward.

## Configuration

Key settings live in `test_generator/config.py`:

| Setting | Meaning |
| --- | --- |
| `LLM_MODEL` | Model id (default `deepseek-chat`) |
| `LLM_MAX_TOKENS` | Completion budget (reasoning + output) |
| `LLM_REASONING_EFFORT` | `minimal` / `low` / `medium` / `high` |
| `MAX_RETRIES` | Repair attempts per method |
| `TEST_TIMEOUT`, `MAVEN_TIMEOUT` | Per-test / per-build timeouts (seconds) |

## Changing the model

This pipeline talks to **DeepSeek** through `test_generator/src/llm_client.py`,
using the OpenAI SDK against DeepSeek's OpenAI-compatible endpoint
(`https://api.deepseek.com`). The client auto-detects reasoning vs. standard models.

**To use a different DeepSeek model — no code changes:**

- Edit `LLM_MODEL` in `test_generator/config.py`. Examples: `deepseek-chat`
  (default, standard) or `deepseek-reasoner` (reasoning).
- **Reasoning models** (`deepseek-reasoner`; also OpenAI `gpt-5*`/`o1`/`o3`/`o4` if you
  switch vendor): `LLM_REASONING_EFFORT` applies and temperature is ignored; the
  budget is sent as `max_completion_tokens`.
- **Standard models** (`gpt-4o`, etc.): `LLM_TEMPERATURE` applies and reasoning effort
  is ignored.
- `OPENAI_API_KEY` is unchanged. `LLM_MAX_TOKENS` still applies.

**To switch to a different vendor** (Anthropic, Google, DeepSeek, …):

Three steps: **(1)** replace `src/llm_client.py` with one that calls the new SDK but
keeps the **exact same contract** — `call_llm(prompt)` returns the response text as a
`str`, or `None` on failure; **(2)** update `requirements.txt` (remove `openai` if
unused); **(3)** set the new key in `.env` and reference it in `config.py`.

Drop-in `src/llm_client.py` for each vendor (the rest of the pipeline is unchanged):

<details><summary><b>Anthropic (Claude)</b></summary>

```python
import time
import anthropic
import config

client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

def call_llm(prompt):
    try:
        resp = client.messages.create(
            model=config.LLM_MODEL,              # e.g. 'claude-sonnet-4-6'
            max_tokens=config.LLM_MAX_TOKENS,
            temperature=config.LLM_TEMPERATURE,
            messages=[{"role": "user", "content": prompt}],
        )
        time.sleep(config.API_SLEEP_SEC)
        return "".join(b.text for b in resp.content if b.type == "text") or None
    except Exception as e:
        print(f"  API Error: {type(e).__name__}: {e}")
        return None
```
- `requirements.txt`: `anthropic`
- `config.py`: `ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")`; `LLM_MODEL = 'claude-sonnet-4-6'`
- `.env`: `ANTHROPIC_API_KEY=...`
</details>

<details><summary><b>Google (Gemini)</b></summary>

```python
import time
import google.generativeai as genai           # SDK: google-generativeai (legacy)
import config

genai.configure(api_key=config.GEMINI_API_KEY)
_model = genai.GenerativeModel(config.LLM_MODEL)   # e.g. 'gemini-2.5-pro'

def call_llm(prompt):
    try:
        resp = _model.generate_content(
            prompt,
            generation_config={"temperature": config.LLM_TEMPERATURE,
                               "max_output_tokens": config.LLM_MAX_TOKENS},
        )
        time.sleep(config.API_SLEEP_SEC)
        return resp.text or None
    except Exception as e:
        print(f"  API Error: {type(e).__name__}: {e}")
        return None
```
- `requirements.txt`: `google-generativeai`  (Google also ships a newer `google-genai` SDK with a different call style — adjust if you use it)
- `config.py`: `GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")`; `LLM_MODEL = 'gemini-2.5-pro'`
- `.env`: `GEMINI_API_KEY=...`
</details>

<details><summary><b>DeepSeek (OpenAI-compatible — easiest)</b></summary>

DeepSeek serves an OpenAI-compatible API, so the existing OpenAI client needs only a
different key and `base_url`:

```python
client = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
```
- keep `openai` in `requirements.txt`
- `config.py`: `DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")`; `LLM_MODEL = 'deepseek-chat'`
- `.env`: `DEEPSEEK_API_KEY=...`
- DeepSeek isn't a gpt-5-style reasoning model, so the standard `max_tokens` +
  `temperature` branch applies automatically.
</details>
