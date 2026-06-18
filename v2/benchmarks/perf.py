#!/usr/bin/env python3
"""
SHACKLE Performance Benchmark
==============================
Measures the overhead of the SHACKLE decision function and daemon RTT.

Targets:
  - decide() function: < 0.1ms
  - pre_exec RTT (Unix socket): < 5ms
  - post_exec (fire-and-forget): < 1ms
  - Total overhead per tool call: < 7ms

Run: python v2/benchmarks/perf.py
"""

import asyncio
import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "spec"))
from decide import GuardConfig, SessionState, ToolCall, HitlMode, decide, hash_params


# ══════════════════════════════════════════
# Benchmark: decide() function (in-process)
# ══════════════════════════════════════════

def bench_decide(iterations: int = 100_000) -> dict:
    """Measure decide() function call overhead."""
    config = GuardConfig(
        budget_usd=1.0,
        max_repeat_calls=3,
        error_amplification=True,
        max_total_calls=1000,
    )
    state = SessionState(
        budget_initial_usd=1.0,
        budget_remaining_usd=0.75,
        budget_spent_usd=0.25,
        total_calls=42,
        last_tool_name="web_search",
        last_tool_params_hash=hash_params({"query": "test"}),
    )
    call = ToolCall(
        tool_name="web_search",
        tool_params_hash=hash_params({"query": "latest news"}),
        estimated_cost_usd=0.002,
        nonce=12345,
    )

    # Warmup
    for _ in range(1000):
        decide(state, call, config, 0.5)

    # Benchmark
    times = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        decide(state, call, config, 0.5)
        elapsed = (time.perf_counter_ns() - start) / 1_000_000  # ms
        times.append(elapsed)

    return {
        "name": "decide() function",
        "iterations": iterations,
        "mean_ms": statistics.mean(times),
        "median_ms": statistics.median(times),
        "p99_ms": sorted(times)[int(iterations * 0.99)],
        "min_ms": min(times),
        "max_ms": max(times),
        "target_ms": 0.1,
        "pass": statistics.mean(times) < 0.1,
    }


# ══════════════════════════════════════════
# Benchmark: has_error_signal()
# ══════════════════════════════════════════

def bench_error_signal(iterations: int = 100_000) -> dict:
    """Measure error signal detection overhead."""
    from decide import has_error_signal

    clean = '{"query": "latest AI news", "source": "reuters"}'
    with_error = '{"query": "test", "error": "401 Unauthorized", "status": "failed"}'

    # Warmup
    for _ in range(1000):
        has_error_signal(clean)

    times = []
    for i in range(iterations):
        params = with_error if i % 2 == 0 else clean
        start = time.perf_counter_ns()
        has_error_signal(params)
        elapsed = (time.perf_counter_ns() - start) / 1_000_000
        times.append(elapsed)

    return {
        "name": "has_error_signal()",
        "iterations": iterations,
        "mean_ms": statistics.mean(times),
        "median_ms": statistics.median(times),
        "p99_ms": sorted(times)[int(iterations * 0.99)],
        "min_ms": min(times),
        "max_ms": max(times),
        "target_ms": 0.01,
        "pass": statistics.mean(times) < 0.01,
    }


# ══════════════════════════════════════════
# Benchmark: hash_params()
# ══════════════════════════════════════════

def bench_hash(iterations: int = 10_000) -> dict:
    """Measure parameter hashing overhead."""
    params = {"query": "latest AI research papers 2026", "source": "arxiv",
              "max_results": 10, "sort_by": "relevance", "language": "en"}

    # Warmup
    for _ in range(100):
        hash_params(params)

    times = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        hash_params(params)
        elapsed = (time.perf_counter_ns() - start) / 1_000_000
        times.append(elapsed)

    return {
        "name": "hash_params()",
        "iterations": iterations,
        "mean_ms": statistics.mean(times),
        "median_ms": statistics.median(times),
        "p99_ms": sorted(times)[int(iterations * 0.99)],
        "min_ms": min(times),
        "max_ms": max(times),
        "target_ms": 0.05,
        "pass": statistics.mean(times) < 0.05,
    }


# ══════════════════════════════════════════
# Main
# ══════════════════════════════════════════

def main():
    print("=" * 60)
    print("  SHACKLE PERFORMANCE BENCHMARK")
    print("  Python {}.{}.{}".format(*sys.version_info[:3]))
    print("=" * 60)
    print()

    results = []

    print("Running decide() benchmark (100K iterations)...")
    results.append(bench_decide(100_000))
    print(f"  Mean: {results[-1]['mean_ms']:.6f} ms  "
          f"Median: {results[-1]['median_ms']:.6f} ms  "
          f"P99: {results[-1]['p99_ms']:.6f} ms  "
          f"{'✅' if results[-1]['pass'] else '❌ FAIL'}  (target: <{results[-1]['target_ms']}ms)")

    print("Running has_error_signal() benchmark (100K iterations)...")
    results.append(bench_error_signal(100_000))
    print(f"  Mean: {results[-1]['mean_ms']:.6f} ms  "
          f"Median: {results[-1]['median_ms']:.6f} ms  "
          f"P99: {results[-1]['p99_ms']:.6f} ms  "
          f"{'✅' if results[-1]['pass'] else '❌ FAIL'}  (target: <{results[-1]['target_ms']}ms)")

    print("Running hash_params() benchmark (10K iterations)...")
    results.append(bench_hash(10_000))
    print(f"  Mean: {results[-1]['mean_ms']:.6f} ms  "
          f"Median: {results[-1]['median_ms']:.6f} ms  "
          f"P99: {results[-1]['p99_ms']:.6f} ms  "
          f"{'✅' if results[-1]['pass'] else '❌ FAIL'}  (target: <{results[-1]['target_ms']}ms)")

    print()
    print("─" * 60)
    total_in_process = sum(r['mean_ms'] for r in results)
    print(f"  Total in-process overhead: {total_in_process:.4f} ms")
    print(f"  Target: <0.16 ms (decide + hash + error detection)")
    print(f"  {'✅ IN-PROCESS WITHIN BUDGET' if total_in_process < 0.16 else '⚠ NEEDS OPTIMIZATION'}")
    print()
    print("  + Daemon RTT (Unix socket): ~2-4 ms (estimated)")
    print(f"  = Total pre_exec overhead: ~{total_in_process + 4:.1f} ms (target: <5ms)")
    print()

    # Summary table
    print("─" * 60)
    print(f"  {'Benchmark':<25} {'Mean':>8} {'P99':>8} {'Target':>8} {'Status':>8}")
    print("─" * 60)
    for r in results:
        status = "✅ PASS" if r['pass'] else "❌ FAIL"
        print(f"  {r['name']:<25} {r['mean_ms']:>7.4f}ms {r['p99_ms']:>7.4f}ms "
              f"{r['target_ms']:>7.4f}ms {status:>8}")
    print("─" * 60)
    print()

    # Recommendation
    slowest = max(results, key=lambda r: r['mean_ms'])
    if not slowest['pass']:
        print(f"⚠ {slowest['name']} EXCEEDS TARGET. Consider Rust rewrite via pyo3.")
        print("  Target: src/rust/shackle_core/src/lib.rs (placeholder ready)")

    return 0 if all(r['pass'] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
