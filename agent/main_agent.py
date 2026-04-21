import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

try:
    import chromadb
except ImportError:
    chromadb = None

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None


class MainAgent:
    """
    Simple RAG agent backed by the existing ChromaDB in ./chroma_db.
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        collection_name: Optional[str] = None,
        model: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-3-small",
        top_k: int = 3,
    ) -> None:
        load_dotenv()

        self.name = "SupportAgent-RAG"
        self.model = model
        self.embedding_model = embedding_model
        self.top_k = top_k

        project_root = Path(__file__).resolve().parent.parent
        self.db_path = str(Path(db_path) if db_path else project_root / "chroma_db")

        api_key = os.getenv("OPENAI_API_KEY")
        self.init_error: Optional[str] = None

        if chromadb is None:
            self.init_error = "Missing dependency 'chromadb'. Run: pip install -r requirements.txt"
            self.llm_client = None
            self.chroma_client = None
            self.collection = None
            return

        if AsyncOpenAI is None:
            self.init_error = "Missing dependency 'openai'. Run: pip install -r requirements.txt"
            self.llm_client = None
            self.chroma_client = None
            self.collection = None
            return

        self.llm_client = AsyncOpenAI(api_key=api_key) if api_key else None
        self.chroma_client = chromadb.PersistentClient(path=self.db_path)
        self.collection = self._load_collection(collection_name)

    def _load_collection(self, collection_name: Optional[str]):
        if collection_name:
            return self.chroma_client.get_collection(collection_name)

        collections = self.chroma_client.list_collections()
        if not collections:
            raise ValueError(f"No Chroma collections found in '{self.db_path}'.")

        return self.chroma_client.get_collection(collections[0].name)

    async def query(self, question: str) -> Dict[str, Any]:
        if self.init_error:
            return {
                "answer": self.init_error,
                "contexts": [],
                "metadata": {
                    "model": self.model,
                    "embedding_model": self.embedding_model,
                    "collection": None,
                    "tokens_used": 0,
                    "sources": [],
                },
            }

        contexts, context_items = await self._retrieve(question)
        answer, tokens_used = await self._generate(question, context_items)

        sources = []
        for item in context_items:
            source = item["metadata"].get("source")
            if source and source not in sources:
                sources.append(source)

        return {
            "answer": answer,
            "contexts": contexts,
            "metadata": {
                "model": self.model,
                "embedding_model": self.embedding_model,
                "collection": self.collection.name,
                "tokens_used": tokens_used,
                "sources": sources,
            },
        }

    async def _retrieve(self, question: str) -> Tuple[List[str], List[Dict[str, Any]]]:
        if not self.llm_client:
            return [], []

        embedding_response = await self.llm_client.embeddings.create(
            model=self.embedding_model,
            input=question,
        )
        query_vector = embedding_response.data[0].embedding

        result = await asyncio.to_thread(
            self.collection.query,
            query_embeddings=[query_vector],
            n_results=self.top_k,
            include=["documents", "metadatas", "distances"],
        )

        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        context_items: List[Dict[str, Any]] = []
        for index, document in enumerate(documents):
            metadata = metadatas[index] if index < len(metadatas) and metadatas[index] else {}
            distance = distances[index] if index < len(distances) else None
            context_items.append(
                {
                    "document": document,
                    "metadata": metadata,
                    "distance": distance,
                }
            )

        contexts = [item["document"] for item in context_items]
        return contexts, context_items

    async def _generate(self, question: str, context_items: List[Dict[str, Any]]) -> Tuple[str, int]:
        if not self.llm_client:
            return (
                "OPENAI_API_KEY is not configured, so I could not generate an answer.",
                0,
            )

        if not context_items:
            return (
                "I could not find any relevant context in the knowledge base for this question.",
                0,
            )

        context_blocks = []
        for idx, item in enumerate(context_items, start=1):
            metadata = item["metadata"]
            source = metadata.get("source", "unknown")
            section = metadata.get("section", "unknown section")
            context_blocks.append(
                f"[Context {idx}]\n"
                f"Source: {source}\n"
                f"Section: {section}\n"
                f"Content: {item['document']}"
            )

        system_prompt = (
            "You are an internal support assistant. Answer only from the provided context. "
            "If the context is insufficient, say so clearly. Keep the answer concise and factual. "
            "Prefer Vietnamese if the user asks in Vietnamese."
        )
        rendered_context = "\n\n".join(context_blocks)
        user_prompt = (
            f"Question: {question}\n\n"
            f"Retrieved context:\n\n{rendered_context}\n\n"
            "Write a grounded answer and mention the relevant source names briefly."
        )

        response = await self.llm_client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        answer = response.choices[0].message.content or ""
        tokens_used = getattr(response.usage, "total_tokens", 0) if response.usage else 0
        return answer, tokens_used


if __name__ == "__main__":
    agent = MainAgent()

    async def test() -> None:
        resp = await agent.query("Làm thế nào để đổi mật khẩu?")
        print(resp)

    asyncio.run(test())
