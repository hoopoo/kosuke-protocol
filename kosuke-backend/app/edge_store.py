"""Edge storage for the fragment network.

Stores relationships between fragments: fluke connections,
semantic similarities, reflection links, domain crossings,
and meaning gravity connections.
"""

import json
import math
import os
import uuid
from collections import Counter
from datetime import datetime, timezone

from app.fragment_store import FragmentStore
from app.models import (
    ClusterInfo,
    Fragment,
    FragmentEdge,
    GalaxyData,
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

    def generate_gravity_edges(
        self,
        fragment_store: FragmentStore,
        gravity_threshold: float = 0.5,
        epsilon: float = 0.01,
    ) -> list[FragmentEdge]:
        """Generate gravity edges between fragments based on meaning mass.

        Gravity formula:
            gravity(A, B) = (mass_A * mass_B) / (semantic_distance^2 + epsilon)

        If gravity > threshold, create an edge with type="gravity".
        """
        all_fragments = fragment_store.get_all_fragments(limit=1000)
        if len(all_fragments) < 2:
            return []

        fragment_ids = [f.id for f in all_fragments]
        embeddings = fragment_store.get_embeddings(fragment_ids)

        # Build galaxy membership scores
        fragment_id_set = set(fragment_ids)
        edge_dicts = [
            e for e in self.edges
            if str(e["fragment_a"]) in fragment_id_set
            and str(e["fragment_b"]) in fragment_id_set
        ]
        galaxy_data = self.detect_galaxies(fragment_store)
        galaxy_score_map: dict[str, float] = {}
        for cluster in galaxy_data.clusters:
            if cluster.is_galaxy:
                score = min(1.0, (cluster.size / 10.0) + cluster.density)
                for member_id in cluster.member_ids:
                    galaxy_score_map[member_id] = max(
                        galaxy_score_map.get(member_id, 0.0), score
                    )

        # Compute meaning mass for each fragment
        mass_map = _compute_mass_map(all_fragments, edge_dicts, galaxy_score_map)

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
                semantic_distance = 1.0 - similarity

                mass_a = mass_map.get(id_a, 0.0)
                mass_b = mass_map.get(id_b, 0.0)

                gravity = (mass_a * mass_b) / (semantic_distance ** 2 + epsilon)

                if gravity > gravity_threshold:
                    # Check if gravity edge already exists
                    exists = False
                    for e in self.edges:
                        pair = {str(e["fragment_a"]), str(e["fragment_b"])}
                        if pair == {id_a, id_b} and e["relation_type"] == "gravity":
                            exists = True
                            break

                    if not exists:
                        weight = min(1.0, round(gravity / (gravity_threshold * 5), 4))
                        edge = self.add_edge(id_a, id_b, "gravity", weight)
                        new_edges.append(edge)

        return new_edges

    def detect_galaxies(
        self,
        fragment_store: FragmentStore,
        density_threshold: float = 0.3,
    ) -> GalaxyData:
        """Detect clusters using Leiden algorithm and identify galaxies.

        A galaxy is a cluster with:
        - size >= 4
        - density > density_threshold

        Galaxy center = node with highest meaning_mass in the cluster.
        """
        all_fragments = fragment_store.get_all_fragments(limit=1000)
        if len(all_fragments) < 2:
            return GalaxyData(
                clusters=[],
                galaxies=[],
                galaxy_count=0,
                largest_galaxy=0,
                average_cluster_size=0.0,
            )

        fragment_ids = {f.id for f in all_fragments}
        valid_edges = [
            e for e in self.get_all_edges()
            if e.fragment_a in fragment_ids and e.fragment_b in fragment_ids
        ]

        # Build igraph graph for Leiden clustering
        import igraph as ig
        import leidenalg

        # Map fragment IDs to integer indices
        id_list = list(fragment_ids)
        id_to_idx: dict[str, int] = {fid: i for i, fid in enumerate(id_list)}

        g = ig.Graph(n=len(id_list))
        edge_tuples: list[tuple[int, int]] = []
        edge_weights: list[float] = []
        seen_pairs: set[tuple[int, int]] = set()

        for e in valid_edges:
            idx_a = id_to_idx[e.fragment_a]
            idx_b = id_to_idx[e.fragment_b]
            pair = (min(idx_a, idx_b), max(idx_a, idx_b))
            if pair not in seen_pairs and idx_a != idx_b:
                seen_pairs.add(pair)
                edge_tuples.append(pair)
                edge_weights.append(e.weight)

        if edge_tuples:
            g.add_edges(edge_tuples)
            g.es["weight"] = edge_weights

        # Run Leiden algorithm
        if g.ecount() > 0:
            partition = leidenalg.find_partition(
                g,
                leidenalg.ModularityVertexPartition,
                weights="weight",
            )
            membership = partition.membership
        else:
            # No edges: each node is its own cluster
            membership = list(range(len(id_list)))

        # Compute meaning mass for center detection
        edge_dicts = [
            e_dict for e_dict in self.edges
            if str(e_dict["fragment_a"]) in fragment_ids
            and str(e_dict["fragment_b"]) in fragment_ids
        ]
        mass_map = _compute_mass_map(all_fragments, edge_dicts)

        # Domain map for entropy calculation
        frag_domain_map: dict[str, str | None] = {f.id: f.domain for f in all_fragments}

        # Group nodes by cluster
        cluster_members: dict[int, list[str]] = {}
        for i, fid in enumerate(id_list):
            cid = membership[i]
            cluster_members.setdefault(cid, []).append(fid)

        # Build ClusterInfo for each cluster
        clusters: list[ClusterInfo] = []
        for cid, members in sorted(cluster_members.items()):
            size = len(members)

            # Calculate density: edges_in_cluster / possible_edges
            member_set = set(members)
            internal_edges = 0
            for e in valid_edges:
                if e.fragment_a in member_set and e.fragment_b in member_set:
                    internal_edges += 1
            possible_edges = size * (size - 1) / 2 if size >= 2 else 1
            density = internal_edges / possible_edges if possible_edges > 0 else 0.0

            # Domain entropy within the cluster
            cluster_domains = [
                frag_domain_map[fid]
                for fid in members
                if frag_domain_map.get(fid)
            ]
            domain_entropy = _shannon_entropy(cluster_domains)  # type: ignore[arg-type]

            # Galaxy center: node with highest meaning_mass
            center = max(members, key=lambda fid: mass_map.get(fid, 0.0))

            # Galaxy rule: size >= 4 AND density > threshold
            is_galaxy = size >= 4 and density > density_threshold

            clusters.append(
                ClusterInfo(
                    cluster_id=cid,
                    size=size,
                    density=round(density, 4),
                    domain_entropy=round(domain_entropy, 4),
                    center_fragment=center,
                    is_galaxy=is_galaxy,
                    member_ids=members,
                )
            )

        galaxies = [c for c in clusters if c.is_galaxy]
        galaxy_count = len(galaxies)
        largest_galaxy = max((g.size for g in galaxies), default=0)
        avg_size = (
            sum(c.size for c in clusters) / len(clusters) if clusters else 0.0
        )

        return GalaxyData(
            clusters=clusters,
            galaxies=galaxies,
            galaxy_count=galaxy_count,
            largest_galaxy=largest_galaxy,
            average_cluster_size=round(avg_size, 2),
        )

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

        # Compute meaning mass for all fragments
        edge_dicts = [
            e for e in self.edges
            if str(e["fragment_a"]) in fragment_ids and str(e["fragment_b"]) in fragment_ids
        ]

        # Run Leiden clustering for cluster assignments and galaxy scores
        galaxy_data = self.detect_galaxies(fragment_store)

        # Build galaxy membership score map
        galaxy_score_map: dict[str, float] = {}
        for cluster in galaxy_data.clusters:
            if cluster.is_galaxy:
                # Galaxy members get a score based on cluster size and density
                score = min(1.0, (cluster.size / 10.0) + cluster.density)
                for member_id in cluster.member_ids:
                    galaxy_score_map[member_id] = max(
                        galaxy_score_map.get(member_id, 0.0), score
                    )

        mass_map = _compute_mass_map(all_fragments, edge_dicts, galaxy_score_map)

        # Determine gravity hub threshold (top 20% by mass, min mass > 0.3)
        masses = sorted(mass_map.values(), reverse=True)
        hub_threshold = 0.3
        if masses:
            top_index = max(0, math.floor(len(masses) * 0.2) - 1)
            hub_threshold = max(0.3, masses[top_index] if top_index < len(masses) else 0.3)
        node_cluster_map: dict[str, int] = {}
        galaxy_centers: set[str] = set()
        for cluster in galaxy_data.clusters:
            for member_id in cluster.member_ids:
                node_cluster_map[member_id] = cluster.cluster_id
            if cluster.is_galaxy:
                galaxy_centers.add(cluster.center_fragment)

        # Build nodes
        nodes: list[NetworkNode] = []
        for f in all_fragments:
            connected_domains = domain_connections.get(f.id, set())
            is_boundary = len(connected_domains) >= 3

            node_type = "reflection" if f.source == "reflection" else "fragment"
            mass = mass_map.get(f.id, 0.0)
            is_gravity_hub = mass >= hub_threshold and mass > 0.3

            nodes.append(
                NetworkNode(
                    id=f.id,
                    text=f.text,
                    domain=f.domain,
                    type=node_type,
                    is_boundary=is_boundary,
                    meaning_mass=round(mass, 3),
                    is_gravity_hub=is_gravity_hub,
                    cluster_id=node_cluster_map.get(f.id),
                    is_galaxy_center=f.id in galaxy_centers,
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
        """Compute network metrics using Leiden clustering."""
        network = self.build_network(fragment_store)
        galaxy_data = self.detect_galaxies(fragment_store)

        boundary_count = sum(1 for n in network.nodes if n.is_boundary)
        gravity_hub_count = sum(1 for n in network.nodes if n.is_gravity_hub)

        return NetworkMetrics(
            fragments=len(network.nodes),
            edges=len(network.edges),
            clusters=len(galaxy_data.clusters),
            boundary_nodes=boundary_count,
            gravity_hubs=gravity_hub_count,
            galaxy_count=galaxy_data.galaxy_count,
            largest_galaxy=galaxy_data.largest_galaxy,
            average_cluster_size=galaxy_data.average_cluster_size,
        )


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def _compute_mass_map(
    fragments: list[Fragment],
    edge_dicts: list[dict[str, object]],
    galaxy_score_map: dict[str, float] | None = None,
) -> dict[str, float]:
    """Compute meaning mass for each fragment.

    Weighted formula:
        meaning_mass = 0.35 * degree_centrality
                     + 0.25 * reflection_count
                     + 0.20 * domain_entropy
                     + 0.20 * galaxy_membership_score

    - degree_centrality: normalized degree (0-1)
    - reflection_count: normalized reflection link count (0-1, capped at 5)
    - domain_entropy: Shannon entropy of connected domains
    - galaxy_membership_score: score based on galaxy membership (0-1)
    """
    if galaxy_score_map is None:
        galaxy_score_map = {}

    fragment_ids = {f.id for f in fragments}

    # Degree centrality
    degree: Counter[str] = Counter()
    for e in edge_dicts:
        fa = str(e["fragment_a"])
        fb = str(e["fragment_b"])
        if fa in fragment_ids:
            degree[fa] += 1
        if fb in fragment_ids:
            degree[fb] += 1

    max_degree = max(degree.values()) if degree else 1

    # Reflection count per fragment
    reflection_count: Counter[str] = Counter()
    for e in edge_dicts:
        if e["relation_type"] == "reflection_link":
            fa = str(e["fragment_a"])
            fb = str(e["fragment_b"])
            if fa in fragment_ids:
                reflection_count[fa] += 1
            if fb in fragment_ids:
                reflection_count[fb] += 1

    # Domain map
    frag_domain_map: dict[str, str | None] = {}
    for f in fragments:
        frag_domain_map[f.id] = f.domain

    # Connected domains per fragment (for domain entropy)
    connected_domains: dict[str, list[str]] = {fid: [] for fid in fragment_ids}
    for e in edge_dicts:
        fa = str(e["fragment_a"])
        fb = str(e["fragment_b"])
        if fa in fragment_ids and fb in fragment_ids:
            domain_b = frag_domain_map.get(fb)
            domain_a = frag_domain_map.get(fa)
            if domain_b:
                connected_domains[fa].append(domain_b)
            if domain_a:
                connected_domains[fb].append(domain_a)

    # Compute mass with weighted formula
    mass_map: dict[str, float] = {}
    for f in fragments:
        # Normalized degree centrality (0-1)
        deg = degree.get(f.id, 0) / max_degree if max_degree > 0 else 0.0

        # Reflection count (normalized 0-1, capped at 5)
        ref_count = min(reflection_count.get(f.id, 0), 5) / 5.0

        # Domain entropy (normalize by max possible ~3.9 for 15 domains)
        domains = connected_domains.get(f.id, [])
        if f.domain:
            domains = domains + [f.domain]
        entropy = _shannon_entropy(domains)
        normalized_entropy = min(1.0, entropy / 3.9) if entropy > 0 else 0.0

        # Galaxy membership score (0-1)
        galaxy_score = galaxy_score_map.get(f.id, 0.0)

        # Weighted formula
        mass = (
            0.35 * deg
            + 0.25 * ref_count
            + 0.20 * normalized_entropy
            + 0.20 * galaxy_score
        )
        mass_map[f.id] = mass

    return mass_map


def _shannon_entropy(items: list[str]) -> float:
    """Compute Shannon entropy of a list of items."""
    if not items:
        return 0.0
    counts = Counter(items)
    total = len(items)
    entropy = 0.0
    for count in counts.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy
