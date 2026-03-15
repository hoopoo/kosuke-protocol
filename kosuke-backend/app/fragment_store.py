"""Fragment storage using ChromaDB vector database."""

import uuid
from datetime import datetime, timezone

import chromadb

from app.models import Fragment, FragmentCreate


class FragmentStore:
    """Vector memory layer for fragments using ChromaDB."""

    def __init__(self, persist_directory: str = "./chroma_data") -> None:
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(
            name="fragments",
            metadata={"hnsw:space": "cosine"},
        )

    def add_fragment(self, fragment: FragmentCreate) -> Fragment:
        """Add a single fragment to the store."""
        fragment_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        self.collection.add(
            documents=[fragment.text],
            metadatas=[
                {
                    "source": fragment.source,
                    "timestamp": timestamp,
                    "tags": ",".join(fragment.tags) if fragment.tags else "",
                }
            ],
            ids=[fragment_id],
        )

        return Fragment(
            id=fragment_id,
            text=fragment.text,
            source=fragment.source,
            timestamp=timestamp,
            tags=fragment.tags,
        )

    def add_fragments_bulk(self, fragments: list[FragmentCreate]) -> list[Fragment]:
        """Add multiple fragments at once."""
        results = []
        for frag in fragments:
            results.append(self.add_fragment(frag))
        return results

    def get_fragment(self, fragment_id: str) -> Fragment | None:
        """Get a single fragment by ID."""
        result = self.collection.get(ids=[fragment_id], include=["documents", "metadatas"])

        if not result["ids"]:
            return None

        doc = result["documents"][0] if result["documents"] else ""
        meta = result["metadatas"][0] if result["metadatas"] else {}

        return Fragment(
            id=fragment_id,
            text=doc,
            source=meta.get("source", ""),
            timestamp=meta.get("timestamp", ""),
            tags=meta.get("tags", "").split(",") if meta.get("tags") else [],
        )

    def get_all_fragments(self, limit: int = 100, offset: int = 0) -> list[Fragment]:
        """Get all fragments with pagination."""
        result = self.collection.get(
            include=["documents", "metadatas"],
            limit=limit,
            offset=offset,
        )

        fragments = []
        for i, fid in enumerate(result["ids"]):
            doc = result["documents"][i] if result["documents"] else ""
            meta = result["metadatas"][i] if result["metadatas"] else {}
            fragments.append(
                Fragment(
                    id=fid,
                    text=doc,
                    source=meta.get("source", ""),
                    timestamp=meta.get("timestamp", ""),
                    tags=meta.get("tags", "").split(",") if meta.get("tags") else [],
                )
            )
        return fragments

    def count(self) -> int:
        """Return the total number of fragments."""
        return self.collection.count()

    def search_semantic(self, query: str, n: int = 5) -> list[Fragment]:
        """Search fragments by semantic similarity."""
        if self.collection.count() == 0:
            return []

        n = min(n, self.collection.count())
        result = self.collection.query(
            query_texts=[query],
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )

        fragments = []
        for i, fid in enumerate(result["ids"][0]):
            doc = result["documents"][0][i] if result["documents"] else ""
            meta = result["metadatas"][0][i] if result["metadatas"] else {}
            fragments.append(
                Fragment(
                    id=fid,
                    text=doc,
                    source=meta.get("source", ""),
                    timestamp=meta.get("timestamp", ""),
                    tags=meta.get("tags", "").split(",") if meta.get("tags") else [],
                )
            )
        return fragments

    def search_by_tags(self, tags: list[str], n: int = 5) -> list[Fragment]:
        """Search fragments by tags."""
        all_frags = self.get_all_fragments(limit=1000)
        matched = []
        for frag in all_frags:
            if any(tag in frag.tags for tag in tags):
                matched.append(frag)
        return matched[:n]

    def get_random(self, n: int = 5) -> list[Fragment]:
        """Get random fragments."""
        import random

        all_frags = self.get_all_fragments(limit=1000)
        if len(all_frags) <= n:
            return all_frags
        return random.sample(all_frags, n)

    def get_embeddings(self, fragment_ids: list[str]) -> dict[str, list[float]]:
        """Get the embeddings for specific fragments."""
        result = self.collection.get(ids=fragment_ids, include=["embeddings"])
        embeddings: dict[str, list[float]] = {}
        if result["embeddings"] is not None:
            for i, fid in enumerate(result["ids"]):
                embeddings[fid] = list(result["embeddings"][i])
        return embeddings

    def delete_fragment(self, fragment_id: str) -> bool:
        """Delete a fragment by ID."""
        try:
            self.collection.delete(ids=[fragment_id])
            return True
        except Exception:
            return False
