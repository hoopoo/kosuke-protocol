"""Meaning Observatory Engine.

Provides research dashboard data for observing the evolution
of meaning structures in Kosuke Protocol.
"""

import math
from collections import Counter
from typing import Optional

from app.drift_engine import _parse_timestamp, compute_drift
from app.edge_store import EdgeStore, _compute_mass_map
from app.fragment_store import FragmentStore
from app.models import (
    DOMAINS,
    DomainBalanceResult,
    DomainStat,
    EmergingSignal,
    EmergingSignalsResult,
    Fragment,
    GalaxyWatch,
    GalaxyWatchResult,
    ReflectionImpact,
    ReflectionImpactResult,
    TopConcept,
    TopConceptsResult,
)
from app.reflection_store import ReflectionStore


def get_top_concepts(
    fragment_store: FragmentStore,
    edge_store: EdgeStore,
    limit: int = 20,
) -> TopConceptsResult:
    """Rank fragments by meaning_mass and show trends over time."""
    network = edge_store.build_network(fragment_store)
    all_fragments = fragment_store.get_all_fragments(limit=1000)
    frag_map = {f.id: f for f in all_fragments}

    # Build edge count per node
    edge_count_map: Counter[str] = Counter()
    for edge in network.edges:
        edge_count_map[edge.source] += 1
        edge_count_map[edge.target] += 1

    # Get drift data for mass trends
    drift_data = compute_drift(fragment_store, edge_store, mode="monthly")
    mass_trend_map: dict[str, float] = {}
    if len(drift_data.slices) >= 2:
        prev_slice = drift_data.slices[-2]
        curr_slice = drift_data.slices[-1]
        for fid in set(prev_slice.meaning_mass_map) | set(curr_slice.meaning_mass_map):
            m1 = prev_slice.meaning_mass_map.get(fid, 0.0)
            m2 = curr_slice.meaning_mass_map.get(fid, 0.0)
            mass_trend_map[fid] = m2 - m1

    # Sort nodes by meaning_mass descending
    sorted_nodes = sorted(network.nodes, key=lambda n: n.meaning_mass, reverse=True)

    concepts: list[TopConcept] = []
    for node in sorted_nodes[:limit]:
        frag = frag_map.get(node.id)
        concepts.append(TopConcept(
            fragment_id=node.id,
            text=frag.text[:150] if frag else node.text[:150],
            domain=node.domain,
            meaning_mass=round(node.meaning_mass, 4),
            is_gravity_hub=node.is_gravity_hub,
            is_galaxy_center=node.is_galaxy_center,
            edge_count=edge_count_map.get(node.id, 0),
            mass_trend=round(mass_trend_map.get(node.id, 0.0), 4),
        ))

    return TopConceptsResult(
        concepts=concepts,
        total_fragments=len(network.nodes),
    )


def get_galaxy_watch(
    fragment_store: FragmentStore,
    edge_store: EdgeStore,
) -> GalaxyWatchResult:
    """List detected galaxies with details and growth tracking."""
    galaxy_data = edge_store.detect_galaxies(fragment_store)
    all_fragments = fragment_store.get_all_fragments(limit=1000)
    frag_map = {f.id: f for f in all_fragments}

    # Get drift data for growth comparison
    drift_data = compute_drift(fragment_store, edge_store, mode="monthly")

    # Build previous slice galaxy sizes for growth comparison
    prev_galaxy_sizes: dict[str, int] = {}
    if len(drift_data.slices) >= 2:
        prev_slice = drift_data.slices[-2]
        # Approximate: count fragments per "cluster" in previous slice
        # by checking which hub_ids were present
        prev_galaxy_sizes = {
            hid: prev_slice.fragment_count
            for hid in prev_slice.galaxy_centers
        }

    galaxies: list[GalaxyWatch] = []
    for galaxy in galaxy_data.galaxies:
        center_frag = frag_map.get(galaxy.center_fragment)
        member_domains: list[str] = []
        for mid in galaxy.member_ids:
            f = frag_map.get(mid)
            if f and f.domain:
                member_domains.append(f.domain)

        # Estimate growth: current size - previous size for this center
        prev_size = prev_galaxy_sizes.get(galaxy.center_fragment, galaxy.size)
        growth = galaxy.size - prev_size

        galaxies.append(GalaxyWatch(
            cluster_id=galaxy.cluster_id,
            size=galaxy.size,
            density=round(galaxy.density, 4),
            domain_entropy=round(galaxy.domain_entropy, 4),
            center_fragment_id=galaxy.center_fragment,
            center_fragment_text=(
                center_frag.text[:150] if center_frag else ""
            ),
            center_domain=center_frag.domain if center_frag else None,
            member_domains=list(set(member_domains)),
            growth=growth,
        ))

    # Sort by size descending
    galaxies.sort(key=lambda g: g.size, reverse=True)

    return GalaxyWatchResult(
        galaxies=galaxies,
        total_galaxies=len(galaxies),
    )


def get_reflection_impact(
    fragment_store: FragmentStore,
    edge_store: EdgeStore,
    reflection_store: ReflectionStore,
) -> ReflectionImpactResult:
    """Measure the structural impact of each reflection."""
    reflections = reflection_store.get_all_reflections(limit=1000)
    if not reflections:
        return ReflectionImpactResult(
            reflections=[],
            total_reflections=0,
            avg_edges_created=0.0,
            avg_mass_boost=0.0,
        )

    network = edge_store.build_network(fragment_store)
    node_map = {n.id: n for n in network.nodes}
    all_edges = edge_store.get_all_edges()

    # Map fragment IDs to cluster IDs and galaxy membership
    cluster_map: dict[str, int | None] = {n.id: n.cluster_id for n in network.nodes}
    galaxy_centers = {n.id for n in network.nodes if n.is_galaxy_center}

    # Get galaxy data for galaxy membership
    galaxy_data = edge_store.detect_galaxies(fragment_store)
    galaxy_member_set: set[str] = set()
    for g in galaxy_data.galaxies:
        for mid in g.member_ids:
            galaxy_member_set.add(mid)

    # Find reflection fragments (source = "reflection")
    all_fragments = fragment_store.get_all_fragments(limit=1000)
    reflection_fragment_ids = {f.id for f in all_fragments if f.source == "reflection"}

    impacts: list[ReflectionImpact] = []

    for ref in reflections:
        # Count reflection_link edges created by this reflection
        # These connect linked_fragment_ids to a reflection fragment
        ref_edges = 0
        linked_frag_ids = set(ref.linked_fragment_ids)

        for e in all_edges:
            if e.relation_type != "reflection_link":
                continue
            fa, fb = e.fragment_a, e.fragment_b
            # Edge connects a linked fragment to a reflection fragment
            if (fa in linked_frag_ids and fb in reflection_fragment_ids) or \
               (fb in linked_frag_ids and fa in reflection_fragment_ids):
                ref_edges += 1

        # Mass boost: sum of meaning_mass for linked fragments
        mass_boost = 0.0
        for fid in ref.linked_fragment_ids:
            node = node_map.get(fid)
            if node:
                mass_boost += node.meaning_mass

        # Clusters touched
        clusters_touched: set[int] = set()
        galaxies_touched = 0
        for fid in ref.linked_fragment_ids:
            cid = cluster_map.get(fid)
            if cid is not None:
                clusters_touched.add(cid)
            if fid in galaxy_member_set:
                galaxies_touched += 1

        impacts.append(ReflectionImpact(
            reflection_id=ref.id,
            reflection_text=ref.text[:150],
            timestamp=ref.timestamp,
            linked_fragment_count=len(ref.linked_fragment_ids),
            edges_created=ref_edges,
            mass_boost=round(mass_boost, 4),
            clusters_touched=len(clusters_touched),
            galaxies_touched=galaxies_touched,
        ))

    # Sort by mass_boost descending
    impacts.sort(key=lambda r: r.mass_boost, reverse=True)

    avg_edges = sum(r.edges_created for r in impacts) / len(impacts) if impacts else 0.0
    avg_mass = sum(r.mass_boost for r in impacts) / len(impacts) if impacts else 0.0

    return ReflectionImpactResult(
        reflections=impacts,
        total_reflections=len(impacts),
        avg_edges_created=round(avg_edges, 2),
        avg_mass_boost=round(avg_mass, 4),
    )


def get_domain_balance(
    fragment_store: FragmentStore,
    edge_store: EdgeStore,
) -> DomainBalanceResult:
    """Analyze domain distribution and highlight imbalances."""
    network = edge_store.build_network(fragment_store)

    # Count fragments per domain
    domain_fragments: dict[str, list[str]] = {}
    for node in network.nodes:
        domain = node.domain or "untagged"
        domain_fragments.setdefault(domain, []).append(node.id)

    # Count edges per domain
    domain_edge_count: Counter[str] = Counter()
    node_domain_map = {n.id: (n.domain or "untagged") for n in network.nodes}
    for edge in network.edges:
        src_domain = node_domain_map.get(edge.source, "untagged")
        tgt_domain = node_domain_map.get(edge.target, "untagged")
        domain_edge_count[src_domain] += 1
        domain_edge_count[tgt_domain] += 1

    # Mass and hub stats per domain
    domain_mass: dict[str, list[float]] = {}
    domain_hubs: Counter[str] = Counter()
    for node in network.nodes:
        domain = node.domain or "untagged"
        domain_mass.setdefault(domain, []).append(node.meaning_mass)
        if node.is_gravity_hub:
            domain_hubs[domain] += 1

    total_fragments = len(network.nodes)

    domains: list[DomainStat] = []
    for domain, frag_ids in sorted(domain_fragments.items(), key=lambda x: -len(x[1])):
        masses = domain_mass.get(domain, [])
        avg_mass = sum(masses) / len(masses) if masses else 0.0
        domains.append(DomainStat(
            domain=domain,
            fragment_count=len(frag_ids),
            percentage=round(len(frag_ids) / total_fragments * 100, 1) if total_fragments > 0 else 0.0,
            edge_count=domain_edge_count.get(domain, 0),
            avg_meaning_mass=round(avg_mass, 4),
            hub_count=domain_hubs.get(domain, 0),
        ))

    # Identify underrepresented domains (< 5% of fragments or absent from DOMAINS list)
    existing_domains = set(domain_fragments.keys())
    underrepresented: list[str] = []
    for d in DOMAINS:
        if d not in existing_domains:
            underrepresented.append(d)
        elif len(domain_fragments.get(d, [])) / total_fragments < 0.05 if total_fragments > 0 else True:
            underrepresented.append(d)

    # Dominant domains (> 25% of fragments)
    dominant: list[str] = []
    for d, fids in domain_fragments.items():
        if total_fragments > 0 and len(fids) / total_fragments > 0.25:
            dominant.append(d)

    return DomainBalanceResult(
        domains=domains,
        total_fragments=total_fragments,
        underrepresented=underrepresented,
        dominant=dominant,
    )


def get_emerging_signals(
    fragment_store: FragmentStore,
    edge_store: EdgeStore,
    limit: int = 20,
) -> EmergingSignalsResult:
    """Detect fragments with rising meaning_mass.

    Prioritize domain-crossing and reflection-linked nodes.
    """
    network = edge_store.build_network(fragment_store)
    all_fragments = fragment_store.get_all_fragments(limit=1000)
    frag_map = {f.id: f for f in all_fragments}

    # Get drift data for mass change
    drift_data = compute_drift(fragment_store, edge_store, mode="monthly")
    mass_change_map: dict[str, float] = {}
    if len(drift_data.slices) >= 2:
        prev_slice = drift_data.slices[-2]
        curr_slice = drift_data.slices[-1]
        for fid in set(prev_slice.meaning_mass_map) | set(curr_slice.meaning_mass_map):
            m1 = prev_slice.meaning_mass_map.get(fid, 0.0)
            m2 = curr_slice.meaning_mass_map.get(fid, 0.0)
            mass_change_map[fid] = m2 - m1

    # Check which nodes are domain-crossing (boundary fragments)
    boundary_set = {n.id for n in network.nodes if n.is_boundary}

    # Check which nodes have reflection links
    all_edges = edge_store.get_all_edges()
    reflection_linked: set[str] = set()
    for e in all_edges:
        if e.relation_type == "reflection_link":
            reflection_linked.add(e.fragment_a)
            reflection_linked.add(e.fragment_b)

    signals: list[EmergingSignal] = []
    for node in network.nodes:
        mass_change = mass_change_map.get(node.id, 0.0)

        # Only include fragments with positive mass change or
        # newly added fragments with meaningful mass
        if mass_change <= 0 and node.meaning_mass < 0.1:
            continue

        is_domain_crossing = node.id in boundary_set
        is_reflection = node.id in reflection_linked

        # Signal strength: mass change + bonuses for crossing/reflection
        signal = mass_change
        if is_domain_crossing:
            signal += 0.1
        if is_reflection:
            signal += 0.05
        signal += node.meaning_mass * 0.2  # boost for current mass

        if signal <= 0:
            continue

        frag = frag_map.get(node.id)
        signals.append(EmergingSignal(
            fragment_id=node.id,
            text=frag.text[:150] if frag else node.text[:150],
            domain=node.domain,
            current_mass=round(node.meaning_mass, 4),
            mass_change=round(mass_change, 4),
            is_domain_crossing=is_domain_crossing,
            is_reflection_linked=is_reflection,
            signal_strength=round(signal, 4),
        ))

    # Sort by signal strength descending
    signals.sort(key=lambda s: s.signal_strength, reverse=True)

    return EmergingSignalsResult(
        signals=signals[:limit],
        total_signals=len(signals),
    )
