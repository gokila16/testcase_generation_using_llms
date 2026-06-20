import json
import os
from datetime import datetime

def load_results(results_path):
    if os.path.exists(results_path):
        # Check if file is empty
        if os.path.getsize(results_path) == 0:
            return {}
        with open(results_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_result(results_path, full_name, result):
    """
    Saves a single result to results.json
    Loads existing results first to avoid overwriting
    """
    # Create the folder if it doesn't exist
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    
    results = load_results(results_path)
    result['timestamp'] = str(datetime.now())
    results[full_name] = result

    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

def is_already_processed(results_path, full_name):
    """
    Checks if a method was already processed
    """
    results = load_results(results_path)
    return full_name in results


_EMPTY_USAGE = {
    'calls': 0,
    'prompt_tokens': 0,
    'completion_tokens': 0,
    'reasoning_tokens': 0,
    'total_tokens': 0,
}


def load_usage(usage_path):
    """Load cumulative token totals persisted from previous runs."""
    if os.path.exists(usage_path) and os.path.getsize(usage_path) > 0:
        with open(usage_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return dict(_EMPTY_USAGE)


def save_usage(usage_path, usage):
    """Persist cumulative token totals (raw counts only, no derived cost)."""
    os.makedirs(os.path.dirname(usage_path), exist_ok=True)
    payload = {k: usage.get(k, 0) for k in _EMPTY_USAGE}
    with open(usage_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)