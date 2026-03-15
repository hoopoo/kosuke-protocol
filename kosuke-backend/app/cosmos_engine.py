"""Collective Cosmos Engine.

Enables multi-author fragment ecosystems where different users
contribute fragments and their meaning networks interact.
"""

import math
from collections import Counter

from app.edge_store import EdgeStore, _cosine_similarity
from app.fragment_store import FragmentStore
from app.models import (
    CollectiveHub,
    CosmosAuthor,
    CosmosData,
    CrossCosmosEdge,
    SharedGalaxy,
)


def analyze_cosmos(
    fragment_store: FragmentStore,
    edge_store: EdgeStore,
    similarity_threshold: float = 0.75,
) -> CosmosData:
    """Analyze the collective cosmos across all authors.

    1. Identify all authors and their fragment statistics
    2. Find cross-cosmos edges (semantic similarity across authors)
    3. Detect shared galaxies (clusters with multiple authors)
    4. Compute collective gravity hubs
    """
    network = edge_store.build_network(fragment_store)
    all_fragments = fragment_store.get_all_fragments(limit=1000)
    frag_map = {f.id: f for f in all_fragments}
    node_map = {n.id: n for n in network.nodes}

    # 1. Identify all authors
    author_fragments: dict[str, list[str]] = {}
    for f in all_fragments:
        author = f.author or "anonymous"
        author_fragments.setdefault(author, []).append(f.id)

    # Edge counts per author
    author_edge_count: Counter[str] = Counter()
    for edge in network.edges:
        src_author = frag_map.get(edge.source)
        tgt_author = frag_map.get(edge.target)
        if src_author:
            author_edge_count[src_author.author or "anonymous"] += 1
        if tgt_author:
            author_edge_count[tgt_author.author or "anonymous"] += 1

    # Hub and galaxy counts per author
    author_hub_count: Counter[str] = Counter()
    for node in network.nodes:
        if node.is_gravity_hub:
            author = node.author or "anonymous"
            author_hub_count[author] += 1

    # Galaxy membership per author
    galaxy_data = edge_store.detect_galaxies(fragment_store)
    author_galaxy_count: Counter[str] = Counter()
    for galaxy in galaxy_data.galaxies:
        authors_in_galaxy: set[str] = set()
        for mid in galaxy.member_ids:
            f = frag_map.get(mid)
            if f:
                authors_in_galaxy.add(f.author or "anonymous")
        for a in authors_in_galaxy:
            author_galaxy_count[a] += 1

    # Average meaning mass per author
    author_mass: dict[str, list[float]] = {}
    for node in network.nodes:
        author = node.author or "anonymous"
        author_mass.setdefault(author, []).append(node.meaning_mass)

    authors: list[CosmosAuthor] = []
    for author_name, frag_ids in sorted(author_fragments.items(), key=lambda x: -len(x[1])):
        masses = author_mass.get(author_name, [])
        avg_mass = sum(masses) / len(masses) if masses else 0.0
        authors.append(CosmosAuthor(
            name=author_name,
            fragment_count=len(frag_ids),
            edge_count=author_edge_count.get(author_name, 0),
            gravity_hub_count=author_hub_count.get(author_name, 0),
            galaxy_count=author_galaxy_count.get(author_name, 0),
            avg_meaning_mass=round(avg_mass, 4),
        ))

    # 2. Find cross-cosmos edges
    cross_edges: list[CrossCosmosEdge] = []

    # Check existing edges that cross author boundaries
    for edge in network.edges:
        src_frag = frag_map.get(edge.source)
        tgt_frag = frag_map.get(edge.target)
        if not src_frag or not tgt_frag:
            continue
        src_author = src_frag.author or "anonymous"
        tgt_author = tgt_frag.author or "anonymous"
        if src_author != tgt_author:
            cross_edges.append(CrossCosmosEdge(
                fragment_a_id=edge.source,
                fragment_a_text=src_frag.text[:100],
                fragment_a_author=src_author,
                fragment_b_id=edge.target,
                fragment_b_text=tgt_frag.text[:100],
                fragment_b_author=tgt_author,
                similarity=edge.weight,
                relation_type=edge.relation,
            ))

    # Also discover new cross-author semantic similarities
    # Get embeddings for cross-author comparison
    if len(author_fragments) >= 2:
        fragment_ids = [f.id for f in all_fragments]
        embeddings = fragment_store.get_embeddings(fragment_ids)

        # Compare fragments across different authors (sample to limit computation)
        author_list = list(author_fragments.keys())
        seen_pairs: set[tuple[str, str]] = set()

        # Collect existing cross-edge pairs to avoid duplicates
        for ce in cross_edges:
            pair = tuple(sorted([ce.fragment_a_id, ce.fragment_b_id]))
            seen_pairs.add(pair)  # type: ignore[arg-type]

        for i in range(len(author_list)):
            for j in range(i + 1, len(author_list)):
                a1_frags = author_fragments[author_list[i]]
                a2_frags = author_fragments[author_list[j]]

                # Sample up to 50 fragments per author for cross-comparison
                a1_sample = a1_frags[:50]
                a2_sample = a2_frags[:50]

                for fid_a in a1_sample:
                    if fid_a not in embeddings:
                        continue
                    for fid_b in a2_sample:
                        if fid_b not in embeddings:
                            continue
                        pair = tuple(sorted([fid_a, fid_b]))
                        if pair in seen_pairs:
                            continue

                        sim = _cosine_similarity(embeddings[fid_a], embeddings[fid_b])
                        if sim > similarity_threshold:
                            seen_pairs.add(pair)  # type: ignore[arg-type]
                            fa = frag_map.get(fid_a)
                            fb = frag_map.get(fid_b)
                            if fa and fb:
                                cross_edges.append(CrossCosmosEdge(
                                    fragment_a_id=fid_a,
                                    fragment_a_text=fa.text[:100],
                                    fragment_a_author=fa.author or "anonymous",
                                    fragment_b_id=fid_b,
                                    fragment_b_text=fb.text[:100],
                                    fragment_b_author=fb.author or "anonymous",
                                    similarity=round(sim, 4),
                                    relation_type="cross_cosmos_similarity",
                                ))

    # Sort by similarity descending
    cross_edges.sort(key=lambda e: e.similarity, reverse=True)

    # 3. Detect shared galaxies (galaxies with fragments from multiple authors)
    shared_galaxies: list[SharedGalaxy] = []
    for galaxy in galaxy_data.galaxies:
        author_counts: Counter[str] = Counter()
        for mid in galaxy.member_ids:
            f = frag_map.get(mid)
            if f:
                author_counts[f.author or "anonymous"] += 1

        if len(author_counts) >= 2:
            center_frag = frag_map.get(galaxy.center_fragment)
            shared_galaxies.append(SharedGalaxy(
                cluster_id=galaxy.cluster_id,
                size=galaxy.size,
                density=round(galaxy.density, 4),
                authors=list(author_counts.keys()),
                author_counts=dict(author_counts),
                center_fragment_id=galaxy.center_fragment,
                center_fragment_text=center_frag.text[:100] if center_frag else "",
                center_author=center_frag.author if center_frag else None,
                domain_entropy=round(galaxy.domain_entropy, 4),
            ))

    shared_galaxies.sort(key=lambda g: g.size, reverse=True)

    # 4. Compute collective gravity hubs
    # Count cross-author edges per fragment
    cross_author_edge_count: Counter[str] = Counter()
    for ce in cross_edges:
        cross_author_edge_count[ce.fragment_a_id] += 1
        cross_author_edge_count[ce.fragment_b_id] += 1

    # Edge counts per fragment
    edge_count_map: Counter[str] = Counter()
    for edge in network.edges:
        edge_count_map[edge.source] += 1
        edge_count_map[edge.target] += 1

    collective_hubs: list[CollectiveHub] = []
    for node in network.nodes:
        if node.is_gravity_hub:
            frag = frag_map.get(node.id)
            collective_hubs.append(CollectiveHub(
                fragment_id=node.id,
                text=frag.text[:150] if frag else node.text[:150],
                author=node.author,
                domain=node.domain,
                meaning_mass=round(node.meaning_mass, 4),
                edge_count=edge_count_map.get(node.id, 0),
                cross_author_edges=cross_author_edge_count.get(node.id, 0),
            ))

    # Sort by meaning_mass descending, then by cross_author_edges
    collective_hubs.sort(key=lambda h: (h.meaning_mass, h.cross_author_edges), reverse=True)

    return CosmosData(
        authors=authors,
        cross_cosmos_edges=cross_edges[:100],  # Limit to top 100
        shared_galaxies=shared_galaxies,
        collective_hubs=collective_hubs,
        total_fragments=len(all_fragments),
        total_authors=len(author_fragments),
        total_cross_edges=len(cross_edges),
        total_shared_galaxies=len(shared_galaxies),
    )


def get_author_network(
    fragment_store: FragmentStore,
    edge_store: EdgeStore,
    author: str,
) -> tuple[list[str], int]:
    """Get fragment IDs and edge count for a specific author.

    Returns (fragment_ids, edge_count) for the given author.
    """
    all_fragments = fragment_store.get_all_fragments(limit=1000)
    author_frag_ids = [f.id for f in all_fragments if (f.author or "anonymous") == author]

    all_edges = edge_store.get_all_edges()
    author_frag_set = set(author_frag_ids)
    edge_count = sum(
        1 for e in all_edges
        if e.fragment_a in author_frag_set or e.fragment_b in author_frag_set
    )

    return author_frag_ids, edge_count


def list_authors(
    fragment_store: FragmentStore,
) -> list[str]:
    """Get list of all unique authors."""
    all_fragments = fragment_store.get_all_fragments(limit=1000)
    authors: set[str] = set()
    for f in all_fragments:
        authors.add(f.author or "anonymous")
    return sorted(authors)
