import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional


class RetrievalEvaluator:
    def __init__(self, chunks_export_path: Optional[str] = None):
        project_root = Path(__file__).resolve().parent.parent
        self.chunks_export_path = (
            Path(chunks_export_path) if chunks_export_path else project_root / "data" / "chunks_export.json"
        )
        self.text_to_chunk_id = self._load_chunk_lookup()
        self.stopwords = {
            "ai", "anh", "bao", "bạn", "bị", "bởi", "các", "cần", "cho", "chưa", "có", "còn", "của",
            "cùng", "đã", "đang", "để", "đến", "đủ", "được", "giữ", "giữa", "gì", "gồm", "hãy", "hết",
            "hơn", "khi", "không", "là", "làm", "lại", "lên", "lúc", "mà", "mới", "một", "nếu",
            "ngày", "người", "nhiều", "nhưng", "nhờ", "nói", "ở", "phải", "qua", "ra", "rằng", "rồi",
            "sau", "sẽ", "số", "tại", "tất", "theo", "thì", "thiếu", "thọ", "tôi", "trên", "trong",
            "trước", "từ", "và", "vẫn", "vào", "vì", "với", "vừa", "yêu", "cầu",
        }
        self.refusal_markers = [
            "không thể", "xin lỗi", "từ chối", "vi phạm", "không hỗ trợ", "không cung cấp",
            "không cho phép", "không có quy định nào cho phép", "yêu cầu phê duyệt",
            "bắt buộc", "không được", "không thể thực hiện", "không thể hỗ trợ",
            "không thể cung cấp", "không thể tiết lộ", "không thể cấp", "không thể bỏ qua",
            "không phù hợp", "trái chính sách", "vi phạm chính sách", "vi phạm bảo mật",
        ]

    def _load_chunk_lookup(self) -> Dict[str, str]:
        if not self.chunks_export_path.exists():
            return {}

        with open(self.chunks_export_path, "r", encoding="utf-8") as f:
            exported = json.load(f)

        lookup: Dict[str, str] = {}
        for chunks in exported.values():
            for chunk in chunks:
                text = chunk.get("text")
                chunk_id = chunk.get("id")
                if text and chunk_id and text not in lookup:
                    lookup[text] = chunk_id
        return lookup

    def calculate_hit_rate(self, expected_ids: List[str], retrieved_ids: List[str], top_k: int = 3) -> float:
        """
        Return 1.0 if at least one expected chunk appears in the top-k retrieved chunks, else 0.0.
        """
        if not expected_ids:
            return 1.0 if not retrieved_ids else 0.0

        top_retrieved = retrieved_ids[:top_k]
        hit = any(doc_id in top_retrieved for doc_id in expected_ids)
        return 1.0 if hit else 0.0

    def calculate_mrr(self, expected_ids: List[str], retrieved_ids: List[str]) -> float:
        """
        Return reciprocal rank of the first relevant retrieved chunk. If none are relevant, return 0.0.
        """
        if not expected_ids:
            return 1.0 if not retrieved_ids else 0.0

        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in expected_ids:
                return 1.0 / (i + 1)
        return 0.0

    def _expected_ids_from_case(self, test_case: Dict[str, Any]) -> List[str]:
        expected = test_case.get("expected_retrieval_ids")
        if expected is None:
            expected = test_case.get("relevant_chunk_ids", [])
        return [str(item) for item in expected if item]

    def _retrieved_ids_from_response(self, response: Dict[str, Any]) -> List[str]:
        direct_ids = response.get("retrieved_ids")
        if direct_ids:
            return [str(item) for item in direct_ids if item]

        metadata_ids = response.get("metadata", {}).get("retrieved_ids")
        if metadata_ids:
            return [str(item) for item in metadata_ids if item]

        contexts = response.get("contexts", [])
        recovered_ids: List[str] = []
        for context in contexts:
            chunk_id = self.text_to_chunk_id.get(context)
            if chunk_id and chunk_id not in recovered_ids:
                recovered_ids.append(chunk_id)
        return recovered_ids

    def _normalize(self, text: str) -> str:
        text = unicodedata.normalize("NFKD", text or "")
        text = "".join(char for char in text if not unicodedata.combining(char))
        text = text.lower()
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _tokenize(self, text: str) -> List[str]:
        normalized = self._normalize(text)
        tokens = re.findall(r"[a-z0-9@._/%:-]+", normalized)
        return [token for token in tokens if len(token) > 1 and token not in self.stopwords]

    def _keyword_coverage(self, keywords: List[str], text: str) -> float:
        if not keywords:
            return 1.0
        normalized_text = self._normalize(text)
        hits = sum(1 for keyword in keywords if self._normalize(keyword) in normalized_text)
        return hits / len(keywords)

    def _token_overlap_ratio(self, source_text: str, target_text: str) -> float:
        source_tokens = set(self._tokenize(source_text))
        target_tokens = set(self._tokenize(target_text))
        if not source_tokens:
            return 1.0
        return len(source_tokens & target_tokens) / len(source_tokens)

    def _contains_refusal(self, text: str) -> bool:
        normalized_text = self._normalize(text)
        return any(marker in normalized_text for marker in self.refusal_markers)

    def _unsupported_surface_forms(self, answer: str, support_text: str) -> float:
        answer_forms = set(re.findall(r"(?:https?://\S+|[\w\.-]+@[\w\.-]+|\b\d+\b)", self._normalize(answer)))
        if not answer_forms:
            return 0.0
        normalized_support = self._normalize(support_text)
        unsupported = sum(1 for item in answer_forms if item not in normalized_support)
        return unsupported / len(answer_forms)

    def _faithfulness_score(
        self,
        test_case: Dict[str, Any],
        response: Dict[str, Any],
        retrieval_metrics: Dict[str, Any],
    ) -> float:
        answer = response.get("answer", "")
        expected_behavior = test_case.get("expected_behavior", "ANSWER")
        support_text = " ".join(response.get("contexts", []) + [test_case.get("context", "")]).strip()

        if expected_behavior == "REFUSE":
            refusal_signal = 1.0 if self._contains_refusal(answer) else 0.0
            expected_overlap = self._token_overlap_ratio(test_case.get("expected_answer", ""), answer)
            score = 0.7 * refusal_signal + 0.3 * expected_overlap
            if retrieval_metrics["expected_ids"] and retrieval_metrics["hit_rate"] == 0.0:
                score *= 0.8
            return round(score, 4)

        if expected_behavior == "CLARIFY":
            clarify_markers = ["lam ro", "co the cho biet", "ban co the", "clarify", "more detail"]
            normalized_answer = self._normalize(answer)
            return 1.0 if any(marker in normalized_answer for marker in clarify_markers) else 0.0

        lexical_support = self._token_overlap_ratio(answer, support_text)
        keyword_support = self._keyword_coverage(test_case.get("answer_keywords", []), support_text)
        keyword_in_answer = self._keyword_coverage(test_case.get("answer_keywords", []), answer)
        unsupported_penalty = self._unsupported_surface_forms(answer, support_text + " " + test_case.get("expected_answer", ""))

        score = (
            0.4 * lexical_support
            + 0.2 * keyword_support
            + 0.2 * keyword_in_answer
            + 0.2 * retrieval_metrics["hit_rate"]
            - 0.25 * unsupported_penalty
        )
        return round(max(0.0, min(1.0, score)), 4)

    def _relevancy_score(self, test_case: Dict[str, Any], response: Dict[str, Any]) -> float:
        answer = response.get("answer", "")
        question = test_case.get("question", "")
        expected_answer = test_case.get("expected_answer", "")
        expected_behavior = test_case.get("expected_behavior", "ANSWER")

        if expected_behavior == "REFUSE":
            refusal_score = 1.0 if self._contains_refusal(answer) else 0.0
            expected_overlap = self._token_overlap_ratio(expected_answer, answer)
            question_overlap = self._token_overlap_ratio(question, answer)
            return round(max(0.0, min(1.0, 0.5 * refusal_score + 0.25 * expected_overlap + 0.25 * question_overlap)), 4)

        if expected_behavior == "CLARIFY":
            clarify_markers = ["lam ro", "co the cho biet", "ban co the", "clarify", "more detail"]
            normalized_answer = self._normalize(answer)
            return 1.0 if any(marker in normalized_answer for marker in clarify_markers) else 0.0

        keyword_coverage = self._keyword_coverage(test_case.get("answer_keywords", []), answer)
        expected_overlap = self._token_overlap_ratio(expected_answer, answer)
        question_overlap = self._token_overlap_ratio(question, answer)

        score = 0.4 * keyword_coverage + 0.35 * expected_overlap + 0.25 * question_overlap
        return round(max(0.0, min(1.0, score)), 4)

    def evaluate_case(self, test_case: Dict[str, Any], response: Dict[str, Any], top_k: int = 3) -> Dict[str, Any]:
        expected_ids = self._expected_ids_from_case(test_case)
        retrieved_ids = self._retrieved_ids_from_response(response)

        hit_rate = self.calculate_hit_rate(expected_ids, retrieved_ids, top_k=top_k)
        mrr = self.calculate_mrr(expected_ids, retrieved_ids)

        return {
            "expected_ids": expected_ids,
            "retrieved_ids": retrieved_ids,
            "hit_rate": hit_rate,
            "mrr": mrr,
            "top_k": top_k,
        }

    async def score(self, test_case: Dict[str, Any], response: Dict[str, Any], top_k: int = 3) -> Dict[str, Any]:
        """
        Per-test retrieval scoring used by the benchmark runner.
        """
        case_metrics = self.evaluate_case(test_case, response, top_k=top_k)
        faithfulness = self._faithfulness_score(test_case, response, case_metrics)
        relevancy = self._relevancy_score(test_case, response)
        return {
            "faithfulness": faithfulness,
            "relevancy": relevancy,
            "retrieval": {
                "expected_ids": case_metrics["expected_ids"],
                "retrieved_ids": case_metrics["retrieved_ids"],
                "hit_rate": case_metrics["hit_rate"],
                "mrr": case_metrics["mrr"],
                "top_k": case_metrics["top_k"],
            },
        }

    async def evaluate_batch(self, dataset: List[Dict[str, Any]], top_k: int = 3) -> Dict[str, Any]:
        """
        Score a dataset where each item contains the golden retrieval ids and either:
        - a nested 'response' dict from the agent, or
        - direct 'retrieved_ids'.
        """
        if not dataset:
            return {
                "avg_hit_rate": 0.0,
                "avg_mrr": 0.0,
                "num_cases": 0,
                "cases": [],
            }

        cases: List[Dict[str, Any]] = []
        for item in dataset:
            response = item.get("response", {"retrieved_ids": item.get("retrieved_ids", [])})
            metrics = self.evaluate_case(item, response, top_k=top_k)
            case_result = {
                "question": item.get("question"),
                **metrics,
            }
            cases.append(case_result)

        avg_hit_rate = sum(case["hit_rate"] for case in cases) / len(cases)
        avg_mrr = sum(case["mrr"] for case in cases) / len(cases)

        return {
            "avg_hit_rate": round(avg_hit_rate, 4),
            "avg_mrr": round(avg_mrr, 4),
            "num_cases": len(cases),
            "cases": cases,
        }
