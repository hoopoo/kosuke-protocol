"""Cosmic Drift Engine for tracking meaning evolution over time.

Generates time-sliced networks and tracks how gravity hubs,
galaxies, and meaning structures drift across time periods.
"""

import math
from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from app.edge_store import EdgeStore, _compute_mass_map, _shannon_entropy
from app.fragment_store import FragmentStore
from app.models import (
    ClusterInfo,
    DriftAnalysis,
    DriftVector,
    Fragment,
    TimeSliceMetrics,
)


def _parse_timestamp(ts: str) -> datetime:
    """Parse an ISO timestamp string to datetime."""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return datetime.now(timezone.utc)

def _get_slice_boundaries(
    fragments: list[Fragment],
    mode: str = "monthly",
) -> list[tuple[str, str, str]]:
    """Generate time slice boundaries from fragment timestamps.

    Returns list of (label, start_iso, end_iso) tuples.
    """
    if not fragments:
        return []

    timestamps = [_parse_timestamp(f.timestamp) for f in fragments]
    min_time = min(timestamps)
    max_time = max(timestamps)

    # Normalize everything to UTC-aware datetimes
    if min_time.tzinfo is None:
        min_time = min_time.replace(tzinfo=timezone.utc)
    else:
        min_time = min_time.astimezone(timezone.utc)

    if max_time.tzinfo is None:
        max_time = max_time.replace(tzinfo=timezone.utc)
    else:
        max_time = max_time.astimezone(timezone.utc)

    slices: list[tuple[str, str, str]] = []

    if mode == "monthly":
        current = min_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        while current <= max_time:
            year = current.year
            month = current.month
            label = f"{year}-{month:02d}"

            start = current
            # Next month
            if month == 12:
                end = current.replace(year=year + 1, month=1)
            else:
                end = current.replace(month=month + 1)

            slices.append((label, start.isoformat(), end.isoformat()))
            current = end

    elif mode == "quarterly":
        current = min_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Align to quarter start
        quarter_month = ((current.month - 1) // 3) * 3 + 1
        current = current.replace(month=quarter_month)
        while current <= max_time:
            year = current.year
            quarter = (current.month - 1) // 3 + 1
            label = f"{year}-Q{quarter}"

            start = current
            # Next quarter
            next_month = current.month + 3
            if next_month > 12:
                end = current.replace(year=year + 1, month=next_month - 12)
            else:
                end = current.replace(month=next_month)

            slices.append((label, start.isoformat(), end.isoformat()))
            current = end

    elif mode == "yearly":
        current_year = min_time.year
        while current_year <= max_time.year:
            label = str(current_year)
            start = datetime(current_year, 1, 1, tzinfo=timezone.utc)
            end = datetime(current_year + 1, 1, 1, tzinfo=timezone.utc)
            slices.append((label, start.isoformat(), end.isoformat()))
            current_year += 1

    else:
        # Default: treat all as one slice
        slices.append((
            "all",
            min_time.isoformat(),
            max_time.isoformat(),
        ))

    return slices


def _filter_fragments_by_time(
    fragments: list[Fragment],
    start_iso: str,
    end_iso: str,
) -> list[Fragment]:
    """Filter fragments that fall within the time range [start, end)."""
    start = _parse_timestamp(start_iso)
    end = _parse_timestamp(end_iso)

    result: list[Fragment] = []
    for f in fragments:
        ts = _parse_timestamp(f.timestamp)
        if start <= ts < end:
            result.append(f)
    return result


def _compute_slice_metrics(
    fragments: list[Fragment],
    edge_dicts: list[dict[str, object]],
    slice_label: str,
    start_time: str,
    end_time: str,
) -> TimeSliceMetrics:
    """Compute metrics for a single time slice of fragments."""
    if not fragments:
        return TimeSliceMetrics(
            slice_label=slice_label,
            start_time=start_time,
            end_time=end_time,
            fragment_count=0,
            edge_count=0,
            cluster_count=0,
            galaxy_count=0,
            gravity_hub_count=0,
        )

    fragment_ids = {f.id for f in fragments}

    # Filter edges to only those within this slice
    slice_edges = [
        e for e in edge_dicts
        if str(e["fragment_a"]) in fragment_ids
        and str(e["fragment_b"]) in fragment_ids
    ]

    # Compute meaning mass
    mass_map = _compute_mass_map(fragments, slice_edges)

    # Determine gravity hubs (top 20%, min > 0.3)
    masses = sorted(mass_map.values(), reverse=True)
    hub_threshold = 0.3
    if masses:
        top_index = max(0, math.floor(len(masses) * 0.2) - 1)
        hub_threshold = max(
            0.3, masses[top_index] if top_index < len(masses) else 0.3
        )

    hub_ids = [
        fid for fid, mass in mass_map.items()
        if mass >= hub_threshold and mass > 0.3
    ]

    # Simple cluster detection via connected components
    # (lightweight alternative to full Leiden for time slices)
    adjacency: dict[str, set[str]] = {fid: set() for fid in fragment_ids}
    for e in slice_edges:
        fa = str(e["fragment_a"])
        fb = str(e["fragment_b"])
        if fa in adjacency and fb in adjacency:
            adjacency[fa].add(fb)
            adjacency[fb].add(fa)

    visited: set[str] = set()
    clusters: list[set[str]] = []
    for fid in fragment_ids:
        if fid not in visited:
            # BFS to find connected component
            component: set[str] = set()
            queue = [fid]
            while queue:
                node = queue.pop(0)
                if node in visited:
                    continue
                visited.add(node)
                component.add(node)
                for neighbor in adjacency.get(node, set()):
                    if neighbor not in visited:
                        queue.append(neighbor)
            clusters.append(component)

    # Identify galaxies (size >= 4, density > 0.3)
    galaxy_count = 0
    galaxy_centers: list[str] = []
    for cluster in clusters:
        if len(cluster) < 4:
            continue
        # Calculate density
        internal_edges = sum(
            1 for e in slice_edges
            if str(e["fragment_a"]) in cluster
            and str(e["fragment_b"]) in cluster
        )
        possible = len(cluster) * (len(cluster) - 1) / 2
        density = internal_edges / possible if possible > 0 else 0.0
        if density > 0.3:
            galaxy_count += 1
            # Galaxy center = highest mass node
            center = max(cluster, key=lambda fid: mass_map.get(fid, 0.0))
            galaxy_centers.append(center)

    return TimeSliceMetrics(
        slice_label=slice_label,
        start_time=start_time,
        end_time=end_time,
        fragment_count=len(fragments),
        edge_count=len(slice_edges),
        cluster_count=len(clusters),
        galaxy_count=galaxy_count,
        gravity_hub_count=len(hub_ids),
        hub_ids=hub_ids,
        galaxy_centers=galaxy_centers,
        meaning_mass_map={fid: round(m, 4) for fid, m in mass_map.items()},
    )


def _classify_drift(
    mass_t1: float,
    mass_t2: float,
    was_hub: bool,
    is_hub: bool,
) -> str:
    """Classify the drift type between two time slices.

    - emergence: not a hub before, became a hub
    - collapse: was a hub, no longer a hub
    - migration: remained a hub but mass shifted significantly
    - stable: remained a hub with similar mass
    """
    if not was_hub and is_hub:
        return "emergence"
    if was_hub and not is_hub:
        return "collapse"
    if was_hub and is_hub:
        delta = abs(mass_t2 - mass_t1)
        if delta > 0.1:
            return "migration"
        return "stable"
    # Neither hub in t1 nor t2 but still tracked (mass changed)
    if abs(mass_t2 - mass_t1) > 0.15:
        return "migration"
    return "stable"


def compute_drift(
    fragment_store: FragmentStore,
    edge_store: EdgeStore,
    mode: str = "monthly",
) -> DriftAnalysis:
    """Compute full drift analysis across time slices.

    1. Get all fragments and edges
    2. Generate time-sliced boundaries
    3. For each slice, compute clusters, galaxies, meaning_mass, gravity hubs
    4. Track hub movement between consecutive slices
    5. Classify drift types
    """
    all_fragments = fragment_store.get_all_fragments(limit=1000)
    if not all_fragments:
        return DriftAnalysis(
            slices=[],
            drift_vectors=[],
            emergence_count=0,
            migration_count=0,
            collapse_count=0,
            stable_count=0,
            slice_mode=mode,
        )

    all_edge_dicts = edge_store.edges

    # Generate time slice boundaries
    boundaries = _get_slice_boundaries(all_fragments, mode)

    # Build fragment lookup
    frag_map: dict[str, Fragment] = {f.id: f for f in all_fragments}

    # Compute metrics for each slice (cumulative - include all fragments up to end)
    slices: list[TimeSliceMetrics] = []
    for label, start_iso, end_iso in boundaries:
        # Cumulative: include all fragments created before end of this slice
        end_dt = _parse_timestamp(end_iso)
        cumulative_frags = [
            f for f in all_fragments
            if _parse_timestamp(f.timestamp) < end_dt
        ]

        if not cumulative_frags:
            slices.append(TimeSliceMetrics(
                slice_label=label,
                start_time=start_iso,
                end_time=end_iso,
                fragment_count=0,
                edge_count=0,
                cluster_count=0,
                galaxy_count=0,
                gravity_hub_count=0,
            ))
            continue

        metrics = _compute_slice_metrics(
            cumulative_frags, all_edge_dicts, label, start_iso, end_iso
        )
        slices.append(metrics)

    # Compute drift vectors between consecutive slices
    drift_vectors: list[DriftVector] = []
    for i in range(1, len(slices)):
        prev = slices[i - 1]
        curr = slices[i]

        # Track all fragments that were hubs in either slice
        tracked_ids = set(prev.hub_ids) | set(curr.hub_ids)
        # Also track fragments with significant mass change
        all_ids = set(prev.meaning_mass_map.keys()) | set(
            curr.meaning_mass_map.keys()
        )
        for fid in all_ids:
            m1 = prev.meaning_mass_map.get(fid, 0.0)
            m2 = curr.meaning_mass_map.get(fid, 0.0)
            if abs(m2 - m1) > 0.15:
                tracked_ids.add(fid)

        for fid in tracked_ids:
            frag = frag_map.get(fid)
            if not frag:
                continue

            mass_t1 = prev.meaning_mass_map.get(fid, 0.0)
            mass_t2 = curr.meaning_mass_map.get(fid, 0.0)
            was_hub = fid in prev.hub_ids
            is_hub = fid in curr.hub_ids

            drift_type = _classify_drift(mass_t1, mass_t2, was_hub, is_hub)

            drift_vectors.append(DriftVector(
                fragment_id=fid,
                fragment_text=frag.text[:100],
                domain=frag.domain,
                mass_t1=round(mass_t1, 4),
                mass_t2=round(mass_t2, 4),
                mass_delta=round(mass_t2 - mass_t1, 4),
                was_hub_t1=was_hub,
                is_hub_t2=is_hub,
                drift_type=drift_type,
            ))

    # Count drift types
    emergence = sum(1 for d in drift_vectors if d.drift_type == "emergence")
    migration = sum(1 for d in drift_vectors if d.drift_type == "migration")
    collapse = sum(1 for d in drift_vectors if d.drift_type == "collapse")
    stable = sum(1 for d in drift_vectors if d.drift_type == "stable")

    return DriftAnalysis(
        slices=slices,
        drift_vectors=drift_vectors,
        emergence_count=emergence,
        migration_count=migration,
        collapse_count=collapse,
        stable_count=stable,
        slice_mode=mode,
    )
