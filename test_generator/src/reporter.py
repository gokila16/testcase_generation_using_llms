from datetime import datetime
import config


def _format_cost_section(token_usage, total_methods):
    """Build the TOKEN USAGE & COST lines from accumulated usage + config prices.
    Returns [] if no usage was recorded."""
    if not token_usage or not token_usage.get('calls'):
        return []
    calls   = token_usage.get('calls', 0)
    prompt  = token_usage.get('prompt_tokens', 0)
    compl   = token_usage.get('completion_tokens', 0)
    total   = token_usage.get('total_tokens', prompt + compl)
    hit     = token_usage.get('cache_hit_tokens', 0)
    miss    = token_usage.get('cache_miss_tokens', prompt)

    cost = (miss / 1_000_000 * config.PRICE_INPUT_CACHE_MISS_PER_1M
            + hit  / 1_000_000 * config.PRICE_INPUT_CACHE_HIT_PER_1M
            + compl / 1_000_000 * config.PRICE_OUTPUT_PER_1M)
    per_method = f"${cost / total_methods:.4f}" if total_methods else "n/a"

    return [
        "TOKEN USAGE & COST",
        f"  Model:             {config.LLM_MODEL}",
        f"  API calls:         {calls}",
        f"  Prompt tokens:     {prompt}  (cache hit {hit}, miss {miss})",
        f"  Completion tokens: {compl}",
        f"  Total tokens:      {total}",
        f"  Est. cost (USD):   ${cost:.4f}",
        f"  Avg cost / method: {per_method}",
        "  (prices from config.PRICE_*; verify against current DeepSeek pricing)",
        "=" * 40,
    ]


def print_progress(processed, total, results):
    """Prints progress every 10 methods"""
    counts = {}
    for r in results.values():
        s = r.get('status', 'UNKNOWN')
        counts[s] = counts.get(s, 0) + 1

    print(f"\n--- Progress: {processed}/{total} ---")
    for status, count in counts.items():
        print(f"  {status}: {count}")

def print_final_report(results, report_path, start_time, token_usage=None):
    """Prints and saves final report (including token usage + estimated cost)."""
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

    lines += [
        f"Retry triggered:   {retried}",
        f"Retry succeeded:   {retry_success}",
        f"Total time:        {elapsed} minutes",
        "=" * 40,
    ]

    lines += _format_cost_section(token_usage, total)

    report = '\n'.join(lines)
    print(report)

    with open(report_path, 'w') as f:
        f.write(report)