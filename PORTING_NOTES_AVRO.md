# Avro 1.12.1 port of the LLM test-generation pipeline — change log

Ports the PDFBox pipeline (`test-case-generation-using-llms`) to **Apache Avro 1.12.1**
(core `org.apache.avro` module). Both pipeline variants are included:

- **v7 (SAGE)** — `test_generator/` — from branch `SAGE-v7`, model `claude-sonnet-4-6`.
  Plan → generate → static allowlist check → compile/run → repair. Uses all 4 inputs.
- **v1 (prompt-and-repair)** — `test_generator_v1/` — from branch `prompt-and-repair`,
  model `gpt-5-mini`. Simpler prompt+repair loop. Uses only `extracted_metadata_final.json`.

## Layout
```
avro_pipeline/                      <- REPO_ROOT for both pipelines
  inputs/                           the 4 Understand-derived Avro inputs
    extracted_metadata_final.json   (1500 methods)
    class_inventory.json            (408 classes)
    dependency_chains.json          (1499 keys)
    call_graph.json                 (1499 keys)
  test_generator/                   v7 pipeline (Avro-configured)
  test_generator_v1/                v1 pipeline (Avro-configured)
  .env                              tool paths (filled) + API keys (blank)
  .env.example                      template
```
The Maven target is NOT bundled: both configs point at the in-place Avro module
`Apache_Avro/avro/lang/java/avro`, which builds and runs tests as-is.

## EXACT changes made (this is the entire diff vs the PDFBox originals)

### 1. `test_generator/config.py` (v7) — values only, no logic
- `PDFBOX_REPO` → `...\Apache_Avro\avro\lang\java`
- `PDFBOX_DIR`  → `...\Apache_Avro\avro\lang\java\avro`  (the avro core Maven module)
- Added a comment block explaining the retarget.
- Everything else is DERIVED and auto-corrects: `TEST_RESOURCES_DIR` (= PDFBOX_DIR/src/test/resources),
  `INPUTS_DIR`, `INPUT_JSON`, `DEPENDENCY_CHAINS_FILE`, `CALL_GRAPH_FILE`, `CLASS_INVENTORY_FILE`,
  `OUTPUT_DIR`, `GENERATED_TESTS_DIR`. Variable names kept as `PDFBOX_*` so that
  `maven_runner.py` and `file_manager.py` (which read `config.PDFBOX_DIR`) need NO edits.

### 2. `test_generator_v1/config.py` (v1) — values only, no logic
- Same two path repoints (`PDFBOX_REPO`, `PDFBOX_DIR`) + comment block.

### 3. `test_generator/src/java_post_processor.py` (v7) — docstring only
- Two illustrative resource filenames in `_collapse_url_variable`'s docstring:
  `file.pdf` → `record.avro`. NO functional/behavioral change (see the file's own
  PORTING CHANGELOG header). All validation/fix logic is byte-identical.

### 4. `test_generator/src/prompt_builder.py` (v7) — in-prompt examples
Several PDF-flavored *examples* were embedded INSIDE the `SYSTEM_PLANNING` and
`SYSTEM_GENERATION` system-prompt templates (i.e. they ARE sent to the LLM, not
just docstrings). Swapped for Avro equivalents:
- naming examples `loadFDF_*` / `getPassword_*`  -> `parse_invalidJson_throwsSchemaParseException`,
  `parse_validJson_returnsRecordSchema`, `getField_unknownName_returnsNull`
- code example `FDFDocument result = Loader.loadFDF(f);` -> `Schema result = new Schema.Parser().parse(json);`
- comment example `// password is "" ... owner password ...` -> `// namespace is null here because the schema was declared without one`
- comment example `// expected 7 pages: cweb.pdf ...` -> `// expected 2 fields: the record declares "id" and "name" ...`
v1's `prompt_builder.py` has NO PDF references in its prompt — left untouched.
Remaining `.pdf`/`pdfbox` strings in v7 prompt_builder are docstring/comment only
(lines 39/41/43 docstring of `_annotate_resource_entry`; line 419 code comment) —
NOT part of any prompt sent to the LLM. The encrypted-file feature is inert for
Avro: it fires only when `test_resource_metadata.json` flags a file as encrypted,
and that file does not exist here, so every resource renders as a plain filename.

### 5. `.env` (new) — machine wiring
- `MAVEN_EXECUTABLE` = installed Maven 3.9.14, `JAVA_HOME` = installed JDK 25 (both verified).
- `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` left blank — fill to run the LLM stage.

### Inputs
- Copied the 4 Avro JSONs (Understand-derived, see ../test_generator builders) into `inputs/`.

### NOT changed (deliberately) — proof the method generalizes
- `maven_runner.py`, `file_manager.py`, `pipeline_step3.py`,
  `allowlist_checker.py`, `cfg_slicer.py`, `context_loader.py`, loaders, etc.: untouched.
- All LOGIC in `prompt_builder.py` is untouched — only the illustrative example
  *strings* inside the prompt templates were swapped (see change #4).

## Verification performed (no API key needed)
- v7 & v1 `config.py` resolve to the real Avro module + all inputs load
  (1500 / 1499 / 1499 / 408).
- Avro module builds: `mvn test-compile` OK; `mvn surefire:test -Dtest=TestSchema`
  → 52 tests, BUILD SUCCESS.
- **End-to-end through the pipeline's own `maven_runner.compile_and_run`** on a
  hand-written test for `org.apache.avro.Schema.create`:
  - v7: COMPILED True, PASSED True
  - v1: COMPILED True, PASSED True
- Safety: generated tests use `*_*_Test.java`; Avro's developer tests use the
  `Test*.java` prefix, so `_clean_stale_generated_tests` never touches them
  (confirmed: 95 Avro tests intact after runs).

## v1 PDFBox audit (line-by-line, separate from v7)

v1 (`test_generator_v1/`, gpt-5-mini) was audited the same way as v7. **Its
generation path is clean — no PDFBox content reaches the LLM prompt or the
generated tests.** Proof:

- v1 has exactly two prompt builders, `build_base_prompt` and
  `build_retry_prompt`. Rendered for `org.apache.avro.Schema.create` and scanned
  for `pdfbox|.pdf|loadFDF|getPassword|FDFDocument|cweb|owner password|PDDocument|COS*`:
  - `build_base_prompt`  -> 3889 chars, **0 PDF hits**  (saved: `rendered_v1_base_prompt.txt`)
  - `build_retry_prompt` -> 1994 chars, **0 PDF hits**
- The generation pipeline (`pipeline_step3.py`) imports ONLY: `loader`,
  `prompt_builder`, `llm_client`, `code_extractor`, `file_manager`,
  `maven_runner`, `result_tracker`, `reporter`. Of these, `prompt_builder`,
  `llm_client`, `code_extractor`, `loader`, `result_tracker`, `reporter` have
  zero PDF references.

Where PDF strings DO still appear in v1 (none affect generation):

| File | Lines | What it is | In prompt / output? |
|---|---|---|---|
| `config.py` | 20-25, 31 | port comments + kept `PDFBOX_*` names (resolve to the Avro module) | No |
| `src/file_manager.py` | 12,13,27,28 | docstring examples (`org.apache.pdfbox.multipdf...`) | No (dev-facing) |
| `src/file_manager.py` | 36, 41 | `config.PDFBOX_DIR` -> Avro module | path only |
| `src/maven_runner.py` | 54, 71 | `cwd=config.PDFBOX_DIR` -> Avro module | path only |
| `resolution_breakdown.py` | 48 | standalone analysis; hardcoded PDFBOX results path default | NOT imported by pipeline |
| `retro_grade.py` | 103,104 | standalone grading tool; docstring examples | NOT imported by pipeline |
| `resource_mismatch_audit.py` | 8,9,54,56,86 | standalone audit with real PDFBox heuristics (CCITT->.tif, FDF rules) | NOT imported by pipeline |

CAVEAT for v1 post-hoc analysis (not generation): `resource_mismatch_audit.py`
encodes PDF-domain heuristics and `resolution_breakdown.py` defaults to a PDFBOX
results path. They are standalone dev/analysis scripts the generation loop never
calls; if used to analyse Avro results they would mislead. Not ported (flagged
here instead). v1 needs no prompt edits (its prompt had no PDF text to begin with).

## What remains to do a FULL run (the only outstanding step)
1. Put an API key in `.env` (`ANTHROPIC_API_KEY` for v7, `OPENAI_API_KEY` for v1).
2. `pip install -r requirements.txt` if running in a fresh venv (deps present here:
   dotenv, anthropic, openai, javalang).
3. Run: from the pipeline dir, `python pipeline_step3.py`.
   Generated tests land in the Avro module's `src/test/java`; results under
   `generated_files/v7` (or `/v1`). Clean generated tests afterward with:
   `find .../avro/.../src/test/java -name "*_*_Test.java" -delete`.
