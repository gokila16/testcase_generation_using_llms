# RQ3 — V7 Ablation Study Specification

**Status:** spec for review (no code changes yet)
**Target:** `RQ3_Ablation_Study/test_generator` (full copy of V7)
**Model:** `gemini-3.5-flash` via Vertex AI (google.genai, `vertexai=True`, ADC auth). Project `testgeneration-497318`, location `global`, temperature=0. Baseline = reuse `test_generator/generated_files/gemini3_v7` (same model) — no re-run.
**Run set:** 1309 methods (`INPUT_JSON = extracted_metadata_final.json`, `INCLUDE_DEVELOPER_TESTED = True`)

---

## 1. Objective

Quantify the contribution of each V7 component via **leave-one-out (LOO)** ablation:
run the full pipeline with all components on (baseline), then re-run with exactly one
component removed at a time, and compare outcome distributions over the same method set.

## 2. Conditions

| ID | Condition | What is removed | Toggle point |
|----|-----------|-----------------|--------------|
| `baseline` | Full V7 | nothing | — |
| `no_slicing` | Method slicing | `testable_slices` → `[]` | pipeline_step3.py:205-211 |
| `no_chains` | Construction chains | `dep_chain` → `None` (both prompts) | pipeline_step3.py:202,211,229 |
| `no_callers` | Caller snippets | `caller_snippets` → `[]` | pipeline_step3.py:203 |
| `no_allowlist` | Allowlist gate | skip import + method-call validation/retry loop | pipeline_step3.py:298-340 (and retry copy ~420) |
| `no_facts` | Pre-computed behavioral facts | `_format_pre_computed_facts` → `""` | prompt_builder.py:284 |
| `no_repair` | Self-repair / retry loop | `MAX_RETRIES=0` + `MAX_ALLOWLIST_RETRIES=0` | config.py:51 + pipeline_step3.py:294 |
| `no_planning` | Two-step planning | `build_one_shot_prompt` replaces plan→generate with one call (same context + reasoning) | prompt_builder.py `build_one_shot_prompt`; pipeline_step3.py planning/one-shot branch |

**7 active ablations + baseline = 8 runs.**

## 3. Mechanism — single `ABLATION` config

Add to `config.py`:

```python
# Each flag True = component ENABLED (baseline). Set one to False per ablation run.
ABLATION = {
    'slicing':   True,
    'chains':    True,
    'callers':   True,
    'allowlist': True,
    'facts':     True,
    'repair':    True,
    'planning':  True,
}
ABLATION_LABEL = 'baseline'   # used to name the output directory
```

Threading (minimal, gated edits — no behavior change when all True):

- **slicing**: in pipeline_step3, if `not ABLATION['slicing']` → `testable_slices = []` (skip slice_method call).
- **chains**: if `not ABLATION['chains']` → pass `dep_chain=None` to both `build_planning_prompt` and `build_generation_from_plan_prompt`.
- **callers**: if `not ABLATION['callers']` → `caller_snippets = []`.
- **allowlist**: if `not ABLATION['allowlist']` → skip the `while` validation loop (treat as passed) in both the main path and the Maven-retry path.
- **facts**: in `_format_pre_computed_facts`, early `return ""` when `not config.ABLATION['facts']` (import config there, or pass a flag in).
- **repair**: if `not ABLATION['repair']` → set effective `max_retries = 0` and `MAX_ALLOWLIST_RETRIES = 0`.
- **planning**: if `not ABLATION['planning']` → call `build_one_shot_prompt` (single LLM call, no separate plan) instead of `build_planning_prompt` + `build_generation_from_plan_prompt`. Same context sections and reasoning guidance; only the two-step decomposition is removed. `plan_response` is `None` (recovery prompt tolerates it).

All edits are guard clauses; with the baseline dict the code path is byte-identical to current V7.

## 4. Output isolation (DONE)

Implemented in `config.py`: outputs are keyed by `ABLATION_LABEL`:

```python
GENRATED_FILES      = os.path.join(BASE_DIR, 'generated_files', f'v7-loo-{ABLATION_LABEL}')
GENERATED_TESTS_DIR = os.path.join(PDFBOX_DIR, f'generated_tests_v7-loo-{ABLATION_LABEL}')
```

Each condition produces its own `prompts/ plans/ responses/ results/results.json` and its own
test source tree compiled by Maven. No cross-contamination. `ABLATION` flag dict is wired into the
pipeline/prompt code; all seven flags (including `planning`) are active.

## 5. Metrics (per condition, from results.json)

Primary: distribution over terminal states —
`PASSED, FAILED, COMPILE_FAILED, ALLOWLIST_FAILED, ALLOWLIST_FAILED_ON_RETRY, EXTRACTION_FAILED, API_ERROR`.

Derived per condition:
- **Pass rate** = PASSED / 1309 (headline).
- **Compile rate** = (PASSED+FAILED) / 1309.
- Δ vs baseline for each, with the failure-mode shift (e.g. removing allowlist → expect ↑COMPILE_FAILED).
- `retry_triggered` / `retry_succeeded` counts (esp. for `no_repair`).
- Optional: line/branch coverage on PASSED tests if RQ wants quality, not just validity.

## 6. Threats to validity

**Model consistency (RESOLVED).** Baseline and ablations both use `gemini-3.5-flash` (Vertex AI,
temp=0). The canonical all-7 baseline is `test_generator/generated_files/gemini3_v7/results.json` —
reuse it directly; no re-run needed since the ablation client now matches that exact model/config.

**Determinism.** Gemini at `temperature=0` is near-deterministic, so a single run per condition is
defensible. (Still worth noting minor run-to-run variation as a limitation; Gemini does not guarantee
bit-identical output even at temp=0.)

## 7. Cost / time

Per method: 2 LLM calls minimum (plan+gen), up to ~8 with retries. 1309 methods × ~2-8 calls
× 7 conditions (×N repeats) is substantial. Plus a Maven compile+run per method.
Recommend: confirm budget, consider a fixed representative **subset** for repeated runs even though
the headline number uses the full 1309 once. (User indicated full 1309 — flag cost before launching.)

## 8. Execution order

1. Implement `ABLATION` dict + output-dir parameterization (guarded, baseline = no-op).
2. Smoke test on ~5 methods with `baseline` to confirm parity with current V7.
3. Run `baseline` (full or subset) → archive results.
4. Run each of the 7 ablations, one flag flipped, own output dir.
5. Aggregate results.json across conditions → comparison table + failure-mode deltas.

## 9. Open decisions

- [ ] N repeats per condition (1 vs ≥3) given gpt-5-mini non-determinism + cost.
- [ ] Full 1309 vs fixed subset for the repeated runs.
- [ ] Coverage metric needed, or pass/compile rates sufficient?
- [ ] Aggregation script: new `RQ3_Ablation_Study/aggregate.py`?
