import asyncio
import json
import os
import time
from typing import Any, Dict, List, Tuple

from agent.main_agent import MainAgent
from engine.llm_judge import LLMJudge
from engine.retrieval_eval import RetrievalEvaluator
from engine.runner import BenchmarkRunner


AGENT_CONFIGS = [
    {
        "version": "Agent_V1_Base",
        "model": os.getenv("AGENT_V1_MODEL", "gpt-4o-mini"),
        "top_k": int(os.getenv("AGENT_V1_TOP_K", "3")),
    },
    {
        "version": "Agent_V2_Optimized",
        "model": os.getenv("AGENT_V2_MODEL", "gpt-4o"),
        "top_k": int(os.getenv("AGENT_V2_TOP_K", "3")),
    },
]

DEFAULT_BATCH_SIZE = int(os.getenv("BENCHMARK_BATCH_SIZE", "5"))

RELEASE_RULES = {
    "min_avg_score": 3.5,
    "min_hit_rate": 0.6,
    "min_agreement_rate": 0.7,
    "max_error_rate": 0.05,
    "max_latency_regression_pct": 0.20,
    "max_cost_regression_pct": 0.30,
}


def load_dataset(path: str = "data/golden_set.jsonl") -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def validate_dataset(dataset: List[Dict[str, Any]]) -> List[str]:
    issues: List[str] = []
    if len(dataset) < 50:
        issues.append(f"Golden dataset only has {len(dataset)} cases; 50+ required.")

    missing_ground_truth_ids = sum(1 for case in dataset if "relevant_chunk_ids" not in case)
    if missing_ground_truth_ids:
        issues.append(f"{missing_ground_truth_ids} cases are missing 'relevant_chunk_ids'.")

    return issues


def aggregate_results(agent_version: str, agent_config: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)
    avg_score = sum(r["judge"]["final_score"] for r in results) / total
    avg_hit_rate = sum(r["ragas"]["retrieval"]["hit_rate"] for r in results) / total
    avg_mrr = sum(r["ragas"]["retrieval"]["mrr"] for r in results) / total
    avg_agreement = sum(r["judge"]["agreement_rate"] for r in results) / total
    avg_latency = sum(r["system"]["latency_seconds"] for r in results) / total
    avg_cost = sum(r["system"]["estimated_cost_usd"] for r in results) / total
    error_rate = sum(1 for r in results if r["system"]["has_error"]) / total
    total_prompt_tokens = sum(r["system"]["prompt_tokens"] for r in results)
    total_completion_tokens = sum(r["system"]["completion_tokens"] for r in results)
    total_tokens = sum(r["system"]["total_tokens"] for r in results)
    total_cost_usd = sum(r["system"]["estimated_cost_usd"] for r in results)
    max_latency = max(r["system"]["latency_seconds"] for r in results)
    min_latency = min(r["system"]["latency_seconds"] for r in results)
    pass_count = sum(1 for r in results if r["status"] == "pass")
    fail_count = total - pass_count

    return {
        "metadata": {
            "version": agent_version,
            "total": total,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "metrics": {
            "avg_score": round(avg_score, 4),
            "hit_rate": round(avg_hit_rate, 4),
            "agreement_rate": round(avg_agreement, 4),
            "mrr": round(avg_mrr, 4),
            "avg_latency_seconds": round(avg_latency, 4),
            "avg_cost_usd": round(avg_cost, 6),
            "error_rate": round(error_rate, 4),
        },
        "system": {
            "batch_size": agent_config["batch_size"],
            "pass_count": pass_count,
            "fail_count": fail_count,
            "token_usage": {
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "total_tokens": total_tokens,
                "avg_tokens_per_case": round(total_tokens / total, 2),
            },
            "cost_report": {
                "total_cost_usd": round(total_cost_usd, 6),
                "avg_cost_usd": round(avg_cost, 6),
                "estimated_cost_per_1k_cases_usd": round(avg_cost * 1000, 4),
            },
            "latency_report": {
                "min_latency_seconds": round(min_latency, 4),
                "avg_latency_seconds": round(avg_latency, 4),
                "max_latency_seconds": round(max_latency, 4),
            },
        },
    }


def compute_regression(v1_summary: Dict[str, Any], v2_summary: Dict[str, Any]) -> Dict[str, Any]:
    v1_metrics = v1_summary["metrics"]
    v2_metrics = v2_summary["metrics"]

    deltas = {
        "avg_score": round(v2_metrics["avg_score"] - v1_metrics["avg_score"], 4),
        "hit_rate": round(v2_metrics["hit_rate"] - v1_metrics["hit_rate"], 4),
        "mrr": round(v2_metrics["mrr"] - v1_metrics["mrr"], 4),
        "agreement_rate": round(v2_metrics["agreement_rate"] - v1_metrics["agreement_rate"], 4),
        "avg_latency_seconds": round(v2_metrics["avg_latency_seconds"] - v1_metrics["avg_latency_seconds"], 4),
        "avg_cost_usd": round(v2_metrics["avg_cost_usd"] - v1_metrics["avg_cost_usd"], 6),
        "error_rate": round(v2_metrics["error_rate"] - v1_metrics["error_rate"], 4),
    }

    latency_regression_pct = _safe_regression_pct(
        v1_metrics["avg_latency_seconds"], v2_metrics["avg_latency_seconds"]
    )
    cost_regression_pct = _safe_regression_pct(v1_metrics["avg_cost_usd"], v2_metrics["avg_cost_usd"])

    checks = {
        "quality_floor": v2_metrics["avg_score"] >= RELEASE_RULES["min_avg_score"],
        "retrieval_floor": v2_metrics["hit_rate"] >= RELEASE_RULES["min_hit_rate"],
        "judge_floor": v2_metrics["agreement_rate"] >= RELEASE_RULES["min_agreement_rate"],
        "error_floor": v2_metrics["error_rate"] <= RELEASE_RULES["max_error_rate"],
        "no_score_regression": deltas["avg_score"] >= 0,
        "no_hit_rate_regression": deltas["hit_rate"] >= 0,
        "latency_budget": latency_regression_pct <= RELEASE_RULES["max_latency_regression_pct"],
        "cost_budget": cost_regression_pct <= RELEASE_RULES["max_cost_regression_pct"],
    }
    decision = "RELEASE" if all(checks.values()) else "ROLLBACK"

    return {
        "v1": v1_metrics,
        "v2": v2_metrics,
        "deltas": deltas,
        "thresholds": RELEASE_RULES,
        "checks": checks,
        "decision": decision,
    }


def _safe_regression_pct(previous: float, current: float) -> float:
    if previous <= 0:
        return 0.0 if current <= 0 else 1.0
    return round((current - previous) / previous, 4)


async def run_benchmark_with_results(agent_config: Dict[str, Any], dataset: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    version = agent_config["version"]
    print(f"Khoi dong Benchmark cho {version}...")

    agent = MainAgent(model=agent_config["model"], top_k=agent_config["top_k"])
    evaluator = RetrievalEvaluator()
    judge = LLMJudge()
    runner = BenchmarkRunner(agent, evaluator, judge)

    started_at = time.perf_counter()
    results = await runner.run_all(dataset, batch_size=agent_config["batch_size"])
    summary = aggregate_results(version, agent_config, results)
    summary["system"]["runtime_seconds"] = round(time.perf_counter() - started_at, 4)
    return results, summary


def write_reports(v2_results: List[Dict[str, Any]], final_summary: Dict[str, Any]) -> None:
    os.makedirs("reports", exist_ok=True)
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(final_summary, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(v2_results, f, ensure_ascii=False, indent=2)


async def main() -> None:
    pipeline_started_at = time.perf_counter()
    golden_path = "data/golden_set.jsonl"
    if not os.path.exists(golden_path):
        print("Thieu data/golden_set.jsonl. Hay chay 'python data/synthetic_gen.py' truoc.")
        return

    dataset = load_dataset(golden_path)
    if not dataset:
        print("File data/golden_set.jsonl rong. Hay tao it nhat 1 test case.")
        return

    dataset_issues = validate_dataset(dataset)
    if dataset_issues:
        print("Canh bao dataset:")
        for issue in dataset_issues:
            print(f"- {issue}")

    benchmark_configs = [
        {**AGENT_CONFIGS[0], "batch_size": DEFAULT_BATCH_SIZE},
        {**AGENT_CONFIGS[1], "batch_size": DEFAULT_BATCH_SIZE},
    ]
    _, v1_summary = await run_benchmark_with_results(benchmark_configs[0], dataset)
    v2_results, v2_summary = await run_benchmark_with_results(benchmark_configs[1], dataset)
    regression = compute_regression(v1_summary, v2_summary)

    if not v1_summary or not v2_summary:
        print("Khong the chay Benchmark. Kiem tra lai data/golden_set.jsonl.")
        return

    print("\n--- KET QUA SO SANH (REGRESSION) ---")
    delta = v2_summary["metrics"]["avg_score"] - v1_summary["metrics"]["avg_score"]
    print(f"V1 Score: {v1_summary['metrics']['avg_score']}")
    print(f"V2 Score: {v2_summary['metrics']['avg_score']}")
    print(f"Delta: {'+' if delta >= 0 else ''}{delta:.2f}")
    print(f"Pipeline Runtime: {time.perf_counter() - pipeline_started_at:.2f}s")
    print(f"V2 Tokens: {v2_summary['system']['token_usage']['total_tokens']}")
    print(f"V2 Cost (USD): {v2_summary['system']['cost_report']['total_cost_usd']}")

    write_reports(v2_results, v2_summary)

    if regression["decision"] == "RELEASE":
        print("QUYET DINH: CHAP NHAN BAN CAP NHAT (APPROVE)")
    else:
        print("QUYET DINH: TU CHOI (BLOCK RELEASE)")


if __name__ == "__main__":
    asyncio.run(main())
