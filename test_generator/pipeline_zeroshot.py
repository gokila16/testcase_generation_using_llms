#!/usr/bin/env python3
"""Zero-shot baseline: single shot, no context, no repair.

For each method in inputs/extracted_metadata_final.json:
  1. Build the zero-shot prompt (focal method only).
  2. Call the LLM once.
  3. Extract the test, compile and run it in Maven.
  4. Record the status (PASSED / FAILED / COMPILE_FAILED / API_ERROR / EXTRACTION_FAILED).

Resumable: methods already in results.json are skipped.
"""

from collections import Counter
from datetime import datetime

import config
from src.loader import load_methods
from src.prompt_builder import build_zeroshot_prompt
from src.llm_client import call_llm
from src.code_extractor import extract_java_code
from src.file_manager import save_prompt, save_response, save_test_file, get_test_class_name
from src.maven_runner import compile_and_run
from src.result_tracker import load_results, save_result, is_already_processed
from src.reporter import print_progress


def assign_unique_keys(methods):
    """Give each method a unique results key; overloads get a numeric suffix."""
    counts = Counter(m['full_name'] for m in methods)
    seen = Counter()
    for m in methods:
        fn = m['full_name']
        if counts[fn] > 1:
            m['unique_key'] = f"{fn}_overload_{seen[fn]}"
            m['overload_index'] = seen[fn]
        else:
            m['unique_key'] = fn
            m['overload_index'] = None
        seen[fn] += 1
    return methods


def print_report(results, report_path, start_time):
    """Status-only tally (this baseline never repairs)."""
    total = len(results)
    counts = {}
    for r in results.values():
        s = r.get('status', 'UNKNOWN')
        counts[s] = counts.get(s, 0) + 1

    elapsed = (datetime.now() - start_time).seconds // 60
    lines = ["=" * 40, "ZERO-SHOT FINAL RESULTS", "=" * 40, f"Total methods:     {total}"]
    for status, count in sorted(counts.items()):
        pct = count / total * 100 if total else 0
        lines.append(f"{status:<20} {count} ({pct:.1f}%)")
    lines += [f"Total time:        {elapsed} minutes", "=" * 40]

    report = '\n'.join(lines)
    print(report)
    with open(report_path, 'w') as f:
        f.write(report)


def run_pipeline():
    start_time = datetime.now()
    print("=" * 40)
    print("ZERO-SHOT PIPELINE (single shot, no context, no repair)")
    print(f"Model: {config.ACTIVE_MODEL} ({config.LLM_PROVIDER} -> {config.LLM_MODEL})")
    print("=" * 40)

    methods = assign_unique_keys(load_methods(config.INPUT_JSON))

    existing = load_results(config.RESULTS_JSON)
    remaining = [m for m in methods if not is_already_processed(config.RESULTS_JSON, m['unique_key'])]
    print(f"Already done: {len(existing)}")
    print(f"Remaining:    {len(remaining)}")

    for i, method in enumerate(remaining):
        full_name      = method['full_name']
        unique_key     = method['unique_key']
        class_name     = method['class_name']
        method_name    = method['method_name']
        overload_index = method['overload_index']

        print(f"\n[{i+1}/{len(remaining)}] {method_name}")

        prompt   = build_zeroshot_prompt(method)
        response = call_llm(prompt)

        save_prompt(config.PROMPTS_DIR, unique_key, prompt)
        save_response(config.RESPONSES_DIR, unique_key, response)

        if not response:
            save_result(config.RESULTS_JSON, unique_key, {
                'status': 'API_ERROR', 'error_message': 'No response from LLM',
            })
            continue

        java_code = extract_java_code(response)
        if not java_code:
            save_result(config.RESULTS_JSON, unique_key, {
                'status': 'EXTRACTION_FAILED', 'error_message': 'Could not extract Java code',
            })
            continue

        # For overloads, match the generated class name to the indexed filename.
        if overload_index is not None:
            base_class  = get_test_class_name(class_name, method_name)
            index_class = get_test_class_name(class_name, method_name, overload_index)
            java_code = java_code.replace(base_class, index_class)

        test_path = save_test_file(
            config.GENERATED_TESTS_DIR, full_name, class_name, method_name, java_code, overload_index
        )

        compiled, passed, error = compile_and_run(
            test_path, full_name, class_name, method_name, overload_index
        )

        if not compiled:
            status = 'COMPILE_FAILED'
        elif not passed:
            status = 'FAILED'
        else:
            status = 'PASSED'

        save_result(config.RESULTS_JSON, unique_key, {
            'status': status, 'error_message': error, 'test_file': test_path,
        })

        if (i + 1) % 10 == 0:
            print_progress(i + 1, len(remaining), load_results(config.RESULTS_JSON))

    print_report(load_results(config.RESULTS_JSON), config.FINAL_REPORT, start_time)


if __name__ == '__main__':
    run_pipeline()
