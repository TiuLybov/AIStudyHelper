import json
from pathlib import Path
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class RagStore:
    def __init__(self, kb_path: str):
        self._path = Path(kb_path)
        self._docs: list[dict[str, Any]] = []
        self._vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=20000)
        self._matrix = None
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return

        if not self._path.exists():
            self._loaded = True
            return

        docs: list[dict[str, Any]] = []
        with self._path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                if "text" not in item:
                    continue
                docs.append(item)

        if docs:
            self._docs = docs
            self._matrix = self._vectorizer.fit_transform([d["text"] for d in docs])
        self._loaded = True

    def retrieve(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        self._load()
        if not self._docs or self._matrix is None:
            return []

        q = self._vectorizer.transform([query])
        scores = cosine_similarity(q, self._matrix)[0]
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
        return [{**self._docs[idx], "score": float(score)} for idx, score in ranked]
