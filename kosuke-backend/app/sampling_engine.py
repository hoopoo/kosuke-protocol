"""Sampling engine for fragment retrieval."""

import random
from datetime import datetime

from app.fragment_store import FragmentStore
from app.models import Fragment


class SamplingEngine:
    """Retrieves fragments through various sampling strategies."""

    def __init__(self, store: FragmentStore) -> None:
        self.store = store

    def sample(
        self,
        method: str = "random",
        query: str | None = None,
        tags: list[str] | None = None,
        n: int = 5,
    ) -> list[Fragment]:
        """Sample fragments using the specified method."""
        if method == "random":
            return self._random_sample(n)
        elif method == "semantic":
            if not query:
                return self._random_sample(n)
            return self._semantic_sample(query, n)
        elif method == "thematic":
            if not tags:
                return self._random_sample(n)
            return self._thematic_sample(tags, n)
        elif method == "temporal":
            return self._temporal_sample(n)
        else:
            return self._random_sample(n)

    def _random_sample(self, n: int) -> list[Fragment]:
        """Pure random sampling."""
        return self.store.get_random(n)

    def _semantic_sample(self, query: str, n: int) -> list[Fragment]:
        """Sample by semantic similarity to a query."""
        return self.store.search_semantic(query, n)

    def _thematic_sample(self, tags: list[str], n: int) -> list[Fragment]:
        """Sample fragments matching specific themes/tags."""
        tagged = self.store.search_by_tags(tags, n * 2)
        if len(tagged) <= n:
            return tagged
        return random.sample(tagged, n)

    def _temporal_sample(self, n: int) -> list[Fragment]:
        """Sample fragments weighted toward recent entries."""
        all_frags = self.store.get_all_fragments(limit=1000)
        if len(all_frags) <= n:
            return all_frags

        # Sort by timestamp descending, weight toward recent
        try:
            sorted_frags = sorted(
                all_frags,
                key=lambda f: f.timestamp,
                reverse=True,
            )
        except Exception:
            return random.sample(all_frags, n)

        # Weighted selection favoring recent fragments
        weights = [1.0 / (i + 1) for i in range(len(sorted_frags))]
        total = sum(weights)
        probabilities = [w / total for w in weights]

        selected_indices = set()
        while len(selected_indices) < n:
            idx = random.choices(range(len(sorted_frags)), weights=probabilities, k=1)[0]
            selected_indices.add(idx)

        return [sorted_frags[i] for i in selected_indices]

    def sample_distant_pair(self, n_candidates: int = 10) -> tuple[Fragment, Fragment] | None:
        """Sample a pair of maximally distant fragments for fluke generation."""
        candidates = self.store.get_random(min(n_candidates, self.store.count()))
        if len(candidates) < 2:
            return None

        # Get embeddings for all candidates
        candidate_ids = [f.id for f in candidates]
        embeddings = self.store.get_embeddings(candidate_ids)

        if len(embeddings) < 2:
            # Fallback: return random pair
            pair = random.sample(candidates, 2)
            return (pair[0], pair[1])

        # Find the most distant pair using cosine distance
        max_distance = -1.0
        best_pair: tuple[Fragment, Fragment] | None = None

        for i in range(len(candidates)):
            for j in range(i + 1, len(candidates)):
                id_a = candidates[i].id
                id_b = candidates[j].id
                if id_a in embeddings and id_b in embeddings:
                    dist = self._cosine_distance(embeddings[id_a], embeddings[id_b])
                    if dist > max_distance:
                        max_distance = dist
                        best_pair = (candidates[i], candidates[j])

        return best_pair

    @staticmethod
    def _cosine_distance(a: list[float], b: list[float]) -> float:
        """Calculate cosine distance between two vectors."""
        import math

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 1.0

        similarity = dot / (norm_a * norm_b)
        return 1.0 - similarity
