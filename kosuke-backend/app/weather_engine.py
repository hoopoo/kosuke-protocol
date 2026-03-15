"""Meaning Weather Engine for Kosuke Protocol.

Computes the "volatility of meaning" in the network by analyzing:
1. New edge rate - how many edges were created recently
2. Cluster change rate - how cluster structure has shifted
3. Gravity hub change - changes in gravity hub composition
4. Galaxy membership shift - changes in galaxy membership

Outputs a weather state: calm, breeze, active, storm, turbulence
"""

import json
import os
from datetime import datetime, timedelta, timezone

from app.edge_store import EdgeStore
from app.fragment_store import FragmentStore
from app.models import MeaningWeather, WeatherSnapshot


def _load_snapshot(path: str) -> WeatherSnapshot | None:
    """Load the previous weather snapshot from disk."""
    if os.path.exists(path):
        with open(path, "r") as f:
            data = json.load(f)
            return WeatherSnapshot(**data)
    return None


def _save_snapshot(path: str, snapshot: WeatherSnapshot) -> None:
    """Save the current weather snapshot to disk."""
    with open(path, "w") as f:
        json.dump(snapshot.model_dump(), f, indent=2)


def _classify_weather(volatility: float) -> str:
    """Classify volatility into a weather state."""
    if volatility < 0.15:
        return "calm"
    elif volatility < 0.35:
        return "breeze"
    elif volatility < 0.55:
        return "active"
    elif volatility < 0.75:
        return "storm"
    else:
        return "turbulence"


def compute_meaning_weather(
    fragment_store: FragmentStore,
    edge_store: EdgeStore,
    snapshot_path: str = "./weather_snapshot.json",
    window_hours: float = 24.0,
) -> MeaningWeather:
    """Compute the current meaning weather.

    Compares the current network state against a previous snapshot
    to determine volatility metrics. If no snapshot exists, this is
    the first reading and volatility will be based on absolute rates.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=window_hours)

    # --- Current state ---
    all_edges = edge_store.get_all_edges()
    total_edges = len(all_edges)

    # Count new edges (created within the window)
    new_edges = 0
    for edge in all_edges:
        try:
            created = datetime.fromisoformat(edge.created_at)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if created >= cutoff:
                new_edges += 1
        except (ValueError, TypeError):
            pass

    # Get current network state
    network = edge_store.build_network(fragment_store)
    galaxy_data = edge_store.detect_galaxies(fragment_store)

    current_hub_ids = sorted(
        [n.id for n in network.nodes if n.is_gravity_hub]
    )
    current_cluster_count = len(galaxy_data.clusters)
    current_galaxy_ids = sorted(
        [str(c.cluster_id) for c in galaxy_data.clusters if c.is_galaxy]
    )
    current_galaxy_member_ids = sorted(
        {
            mid
            for c in galaxy_data.clusters
            if c.is_galaxy
            for mid in c.member_ids
        }
    )
    total_fragments = len(network.nodes)

    # --- Load previous snapshot ---
    prev = _load_snapshot(snapshot_path)

    # --- Compute metrics ---

    # 1. New edge rate (normalized by total fragments)
    # More edges relative to network size = higher rate
    new_edge_rate = 0.0
    if total_fragments > 0:
        # Normalize: if new_edges >= total_fragments, rate = 1.0
        new_edge_rate = min(1.0, new_edges / max(total_fragments, 1))

    # 2. Cluster change rate
    cluster_shift = 0.0
    if prev is not None:
        prev_cluster_count = prev.cluster_count
        if prev_cluster_count > 0 or current_cluster_count > 0:
            diff = abs(current_cluster_count - prev_cluster_count)
            max_count = max(prev_cluster_count, current_cluster_count, 1)
            cluster_shift = min(1.0, diff / max_count)
    else:
        # First snapshot: use cluster-to-fragment ratio as baseline
        if total_fragments > 1:
            # If every fragment is its own cluster, shift = 0
            # If fragments are highly clustered, shift is higher
            ideal_clusters = total_fragments
            if current_cluster_count < ideal_clusters:
                cluster_shift = min(
                    1.0,
                    1.0 - (current_cluster_count / ideal_clusters),
                )

    # 3. Gravity hub change
    gravity_change = 0.0
    if prev is not None:
        prev_hub_set = set(prev.hub_ids)
        curr_hub_set = set(current_hub_ids)
        if prev_hub_set or curr_hub_set:
            union = prev_hub_set | curr_hub_set
            symmetric_diff = prev_hub_set ^ curr_hub_set
            gravity_change = len(symmetric_diff) / max(len(union), 1)
    else:
        # First snapshot: if hubs exist, there's some activity
        if current_hub_ids:
            gravity_change = min(1.0, len(current_hub_ids) / max(total_fragments * 0.2, 1))

    # 4. Galaxy membership shift
    galaxy_shift = 0.0
    if prev is not None:
        prev_galaxy_set = set(prev.galaxy_member_ids)
        curr_galaxy_set = set(current_galaxy_member_ids)
        if prev_galaxy_set or curr_galaxy_set:
            union = prev_galaxy_set | curr_galaxy_set
            symmetric_diff = prev_galaxy_set ^ curr_galaxy_set
            galaxy_shift = len(symmetric_diff) / max(len(union), 1)
    else:
        # First snapshot: if galaxies exist, there's been formation activity
        if current_galaxy_member_ids:
            galaxy_shift = min(
                1.0,
                len(current_galaxy_member_ids) / max(total_fragments, 1),
            )

    # --- Composite volatility ---
    volatility = (
        0.30 * new_edge_rate
        + 0.25 * cluster_shift
        + 0.25 * gravity_change
        + 0.20 * galaxy_shift
    )
    volatility = round(min(1.0, volatility), 3)

    weather = _classify_weather(volatility)

    # --- Save current snapshot for next comparison ---
    current_snapshot = WeatherSnapshot(
        timestamp=now.isoformat(),
        total_edges=total_edges,
        total_fragments=total_fragments,
        cluster_count=current_cluster_count,
        hub_ids=current_hub_ids,
        galaxy_ids=current_galaxy_ids,
        galaxy_member_ids=current_galaxy_member_ids,
    )
    _save_snapshot(snapshot_path, current_snapshot)

    return MeaningWeather(
        weather=weather,
        volatility=volatility,
        new_edges=new_edges,
        new_edge_rate=round(new_edge_rate, 3),
        cluster_shift=round(cluster_shift, 3),
        gravity_change=round(gravity_change, 3),
        galaxy_shift=round(galaxy_shift, 3),
        total_edges=total_edges,
        total_fragments=total_fragments,
        total_clusters=current_cluster_count,
        total_hubs=len(current_hub_ids),
        total_galaxies=len(current_galaxy_ids),
        window_hours=window_hours,
        snapshot_exists=prev is not None,
    )
