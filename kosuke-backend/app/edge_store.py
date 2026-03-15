"""Edge storage for the fragment network.

Stores relationships between fragments: fluke connections,
semantic similarities, reflection links, and domain crossings.
"""

import json
import math
import os
import uuid
from datetime import datetime, timezone

from app.fragment_store import FragmentStore
from app.models import (
    Fragment,
    FragmentEdge,
    NetworkData,
    NetworkEdge,
    NetworkMetrics,
    NetworkNode,
)


class EdgeStore:
    """Stores and manages edges between fragments."""

    def __init__(self, storage_path: str = "./edges.json") -> None:
        self.storage_path = storage_path
        self.edges: list[dict[str, object]] = []
        self._load()

    def _load(self) -> None:
        """Load edges from disk."""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, "r") as f:
                self.edges = json.load(f)

    def _save(self) -> None:
        """Persist edges to disk."""
        with open(self.storage_path, "w") as f:
            json.dump(self.edges, f, indent=2)

    def add_edge(
        self,
        fragment_a_id: str,
        fragment_b_id: str,
        relation_type: str,
        weight: float,
    ) -> FragmentEdge:
        """Add an edge between two fragments."""
        # Check for duplicate edges (same pair + same relation type)
        for edge in self.edges:
            pair = {str(edge["fragment_a"]), str(edge["fragment_b"])}
            if pair == {fragment_a_id, fragment_b_id} and edge["relation_type"] == relation_type:
                # Update weight if edge already exists
                edge["weight"] = weight
                self._save()
                return FragmentEdge(**edge)  # type: ignore[arg-type]

        edge_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        data: dict[str, object] = {
            "id": edge_id,
            "fragment_a": fragment_a_id,
            "fragment_b": fragment_b_id,
            "relation_type": relation_type,
            "weight": weight,
            "created_at": timestamp,
        }

        self.edges.append(data)
        self._save()

        return FragmentEdge(**data)  # type: ignore[arg-type]

    def get_all_edges(self) -> list[FragmentEdge]:
        """Get all edges."""
        return [FragmentEdge(**e) for e in self.edges]  # type: ignore[arg-type]

    def get_edges_for_fragment(self, fragment_id: str) -> list[FragmentEdge]:
        """Get all edges connected to a specific fragment."""
        result = []
        for e in self.edges:
            if e["fragment_a"] == fragment_id or e["fragment_b"] == fragment_id:
                result.append(FragmentEdge(**e))  # type: ignore[arg-type]
        return result

    def count(self) -> int:
        """Return total number of edges."""
        return len(self.edges)

    def create_fluke_edge(
        self,
        fragment_a_id: str,
        fragment_b_id: str,
        cosine_distance: float,
    ) -> FragmentEdge:
        """Create an edge from a fluke generation."""
        weight = 1.0 - cosine_distance  # higher similarity = higher weight
        return self.add_edge(fragment_a_id, fragment_b_id, "fluke", max(0.1, weight))

    def create_domain_crossing_edge(
        self,
        fragment_a_id: str,
        fragment_b_id: str,
        weight: float = 0.8,
    ) -> FragmentEdge:
        """Create a domain-crossing edge."""
        return self.add_edge(fragment_a_id, fragment_b_id, "domain_crossing", weight)

    def create_reflection_edge(
        self,
        fragment_id: str,
        reflection_fragment_id: str,
    ) -> FragmentEdge:
        """Create a reflection link edge."""
        return self.add_edge(fragment_id, reflection_fragment_id, "reflection_link", 0.9)

    def generate_semantic_edges(
        self,
        fragment_store: FragmentStore,
        similarity_threshold: float = 0.82,
    ) -> list[FragmentEdge]:
        """Generate semantic similarity edges for all fragment pairs above threshold.

        This is the background job that finds semantically similar fragments.
        """
        all_fragments = fragment_store.get_all_fragments(limit=1000)
        if len(all_fragments) < 2:
            return []

        fragment_ids = [f.id for f in all_fragments]
        embeddings = fragment_store.get_embeddings(fragment_ids)

        new_edges: list[FragmentEdge] = []

        for i in range(len(all_fragments)):
            for j in range(i + 1, len(all_fragments)):
                id_a = all_fragments[i].id
                id_b = all_fragments[j].id

                if id_a not in embeddings or id_b not in embeddings:
                    continue

                emb_a = embeddings[id_a]
                emb_b = embeddings[id_b]

                similarity = _cosine_similarity(emb_a, emb_b)

                if similarity > similarity_threshold:
                    # Check if edge already exists
                    exists = False
                    for e in self.edges:
                        pair = {str(e["fragment_a"]), str(e["fragment_b"])}
                        if pair == {id_a, id_b} and e["relation_type"] == "semantic_similarity":
                            exists = True
                            break

                    if not exists:
                        edge = self.add_edge(
                            id_a, id_b, "semantic_similarity", round(similarity, 4)
                        )
                        new_edges.append(edge)

        return new_edges

    def build_network(
        self,
        fragment_store: FragmentStore,
    ) -> NetworkData:
        """Build the full network data for visualization."""
        all_fragments = fragment_store.get_all_fragments(limit=1000)
        all_edges = self.get_all_edges()

        # Build adjacency info for boundary detection
        fragment_ids = {f.id for f in all_fragments}
        domain_connections: dict[str, set[str]] = {}

        for edge in all_edges:
            if edge.fragment_a not in fragment_ids or edge.fragment_b not in fragment_ids:
                continue
            domain_connections.setdefault(edge.fragment_a, set())
            domain_connections.setdefault(edge.fragment_b, set())

        # Map fragment IDs to their domains
        frag_domain_map: dict[str, str | None] = {}
        for f in all_fragments:
            frag_domain_map[f.id] = f.domain

        # Track connected domains per fragment
        for edge in all_edges:
            if edge.fragment_a not in fragment_ids or edge.fragment_b not in fragment_ids:
                continue
            domain_b = frag_domain_map.get(edge.fragment_b)
            domain_a = frag_domain_map.get(edge.fragment_a)
            if domain_b:
                domain_connections.setdefault(edge.fragment_a, set()).add(domain_b)
            if domain_a:
                domain_connections.setdefault(edge.fragment_b, set()).add(domain_a)
            # Also add own domain
            if domain_a:
                domain_connections.setdefault(edge.fragment_a, set()).add(domain_a)
            if domain_b:
                domain_connections.setdefault(edge.fragment_b, set()).add(domain_b)

        # Build nodes
        nodes: list[NetworkNode] = []
        for f in all_fragments:
            connected_domains = domain_connections.get(f.id, set())
            is_boundary = len(connected_domains) >= 3

            node_type = "reflection" if f.source == "reflection" else "fragment"

            nodes.append(
                NetworkNode(
                    id=f.id,
                    text=f.text,
                    domain=f.domain,
                    type=node_type,
                    is_boundary=is_boundary,
                )
            )

        # Build edges (only include edges where both fragments exist)
        network_edges: list[NetworkEdge] = []
        for edge in all_edges:
            if edge.fragment_a in fragment_ids and edge.fragment_b in fragment_ids:
                network_edges.append(
                    NetworkEdge(
                        source=edge.fragment_a,
                        target=edge.fragment_b,
                        weight=edge.weight,
                        relation=edge.relation_type,
                    )
                )

        return NetworkData(nodes=nodes, edges=network_edges)

    def get_metrics(self, fragment_store: FragmentStore) -> NetworkMetrics:
        """Compute network metrics."""
        network = self.build_network(fragment_store)

        # Simple cluster detection using connected components
        adj: dict[str, set[str]] = {}
        for node in network.nodes:
            adj[node.id] = set()
        for edge in network.edges:
            adj.setdefault(edge.source, set()).add(edge.target)
            adj.setdefault(edge.target, set()).add(edge.source)

        visited: set[str] = set()
        clusters = 0
        for node_id in adj:
            if node_id not in visited:
                clusters += 1
                # BFS
                queue = [node_id]
                while queue:
                    current = queue.pop(0)
                    if current in visited:
                        continue
                    visited.add(current)
                    for neighbor in adj.get(current, set()):
                        if neighbor not in visited:
                            queue.append(neighbor)

        boundary_count = sum(1 for n in network.nodes if n.is_boundary)

        return NetworkMetrics(
            fragments=len(network.nodes),
            edges=len(network.edges),
            clusters=clusters,
            boundary_nodes=boundary_count,
        )


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)
