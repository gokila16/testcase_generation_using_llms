from datetime import datetime

def print_progress(processed, total, results, usage=None):
    """Prints progress every 10 methods"""
    counts = {}
    for r in results.values():
        s = r.get('status', 'UNKNOWN')
        counts[s] = counts.get(s, 0) + 1

    print(f"\n--- Progress: {processed}/{total} ---")
    for status, count in counts.items():
        print(f"  {status}: {count}")

    if usage:
        print(f"  Tokens so far: {usage['total_tokens']:,} "
              f"(in {usage['prompt_tokens']:,} / out {usage['completion_tokens']:,} "
              f"/ think {usage['reasoning_tokens']:,})"
              f"  |  Cost so far: ${usage['total_cost_usd']:.4f}")

def print_final_report(results, report_path, start_time, truncation_count=0,
                       usage=None, cumulative_usage=None):
    """Prints and saves final report"""
    total = len(results)
    counts = {}
    for r in results.values():
        s = r.get('status', 'UNKNOWN')
        counts[s] = counts.get(s, 0) + 1

    retried = sum(
        1 for r in results.values()
        if r.get('retry_triggered')
    )
    retry_success = sum(
        1 for r in results.values()
        if r.get('retry_succeeded')
    )

    elapsed = (datetime.now() - start_time).seconds // 60

    lines = [
        "=" * 40,
        "FINAL RESULTS",
        "=" * 40,
        f"Total methods:     {total}",
    ]
    for status, count in sorted(counts.items()):
        pct = count / total * 100 if total > 0 else 0
        lines.append(f"{status:<20} {count} ({pct:.1f}%)")

    fail_reasons = {}
    for r in results.values():
        if r.get('status') == 'EXTRACTION_FAILED':
            reason = r.get('extraction_fail_reason') or 'unknown'
            fail_reasons[reason] = fail_reasons.get(reason, 0) + 1

    lines += [
        f"Retry triggered:   {retried}",
        f"Retry succeeded:   {retry_success}",
        f"Truncations cont.: {truncation_count}",
        f"Total time:        {elapsed} minutes",
    ]

    if fail_reasons:
        lines.append("--- Extraction fail reasons ---")
        for reason, count in sorted(fail_reasons.items()):
            lines.append(f"  {reason:<25} {count}")

    if usage:
        lines += [
            "--- Token usage & cost (this run) ---",
            f"API calls:           {usage['calls']:,}",
            f"Input tokens:        {usage['prompt_tokens']:,}",
            f"Output tokens:       {usage['completion_tokens']:,}",
            f"Reasoning tokens:    {usage['reasoning_tokens']:,}",
            f"Billed output:       {usage['output_tokens_billed']:,}  (output + reasoning)",
            f"Total tokens:        {usage['total_tokens']:,}",
            f"Input cost:          ${usage['input_cost_usd']:.4f}",
            f"Output cost:         ${usage['output_cost_usd']:.4f}  (on billed output)",
            f"Total cost:          ${usage['total_cost_usd']:.4f}",
        ]

    if cumulative_usage:
        lines += [
            "--- Token usage & cost (cumulative, all runs) ---",
            f"Total tokens:      {cumulative_usage['total_tokens']:,}",
            f"Total cost:        ${cumulative_usage['total_cost_usd']:.4f}",
        ]

    lines.append("=" * 40)

    report = '\n'.join(lines)
    print(report)

    with open(report_path, 'w') as f:
        f.write(report)