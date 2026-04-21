import asyncio
import time
from typing import List, Dict
# Import other components...

class BenchmarkRunner:
    def __init__(self, agent, evaluator, judge):
        self.agent = agent
        self.evaluator = evaluator
        self.judge = judge

    async def run_single_test(self, test_case: Dict) -> Dict:
        start_time = time.perf_counter()
        
        # 1. Gọi Agent
        response = await self.agent.query(test_case["question"])
        latency = time.perf_counter() - start_time
        
        # 2. Chạy RAGAS metrics
        ragas_scores = await self.evaluator.score(test_case, response)
        
        # 3. Chạy Multi-Judge
        judge_result = await self.judge.evaluate_multi_judge(
            test_case["question"], 
            response["answer"], 
            test_case["expected_answer"]
        )

        system_metrics = self._build_system_metrics(response, judge_result, latency)
        passed = judge_result["final_score"] >= 3 and ragas_scores["retrieval"]["hit_rate"] >= 0.0
        
        return {
            "test_case": test_case["question"],
            "agent_response": response["answer"],
            "latency": latency,
            "ragas": ragas_scores,
            "judge": judge_result,
            "system": system_metrics,
            "status": "pass" if passed else "fail",
        }

    async def run_all(self, dataset: List[Dict], batch_size: int = 5) -> List[Dict]:
        """
        Chạy song song bằng asyncio.gather với giới hạn batch_size để không bị Rate Limit.
        """
        results = []
        for i in range(0, len(dataset), batch_size):
            batch = dataset[i:i + batch_size]
            tasks = [self.run_single_test(case) for case in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
        return results

    def _build_system_metrics(self, response: Dict, judge_result: Dict, latency: float) -> Dict:
        agent_meta = response.get("metadata", {})
        judge_results = judge_result.get("individual_results", [])

        total_prompt_tokens = agent_meta.get("prompt_tokens", 0)
        total_completion_tokens = agent_meta.get("completion_tokens", 0)
        cost_usd = self._estimate_generation_cost(
            agent_meta.get("model"),
            agent_meta.get("prompt_tokens", 0),
            agent_meta.get("completion_tokens", 0),
        )

        for item in judge_results:
            usage = item.get("usage", {})
            total_prompt_tokens += usage.get("prompt_tokens", 0)
            total_completion_tokens += usage.get("completion_tokens", 0)
            cost_usd += self._estimate_generation_cost(
                item.get("model"),
                usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0),
            )

        error_count = 0
        if response.get("answer") == self.agent.init_error:
            error_count += 1
        error_count += sum(1 for item in judge_results if "error" in item)

        return {
            "latency_seconds": round(latency, 4),
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "total_tokens": total_prompt_tokens + total_completion_tokens,
            "estimated_cost_usd": round(cost_usd, 6),
            "error_count": error_count,
            "has_error": error_count > 0,
        }

    def _estimate_generation_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        pricing_per_million = {
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-4o": {"input": 5.00, "output": 15.00},
        }
        model_pricing = pricing_per_million.get(model or "", {"input": 0.0, "output": 0.0})
        return (
            (prompt_tokens / 1_000_000) * model_pricing["input"]
            + (completion_tokens / 1_000_000) * model_pricing["output"]
        )
