"""Kosuke Protocol - An Intelligence Ecosystem for Meaning Generation.

FastAPI backend providing fragment ingestion, vector memory,
sampling, fluke generation, reflection storage, and markdown export.
"""

from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from app.drift_engine import compute_drift
from app.edge_store import EdgeStore
from app.fluke_engine import SlowModeTracker, generate_fluke
from app.fragment_store import FragmentStore
from app.models import (
    DriftAnalysis,
    ExportRequest,
    Fragment,
    FragmentCreate,
    FragmentIngest,
    FlukeRequest,
    FlukeResult,
    GalaxyData,
    NetworkData,
    NetworkMetrics,
    Reflection,
    ReflectionCreate,
    SampleRequest,
    SlowModeConfig,
    SlowModeStatus,
)
from app.reflection_store import ReflectionStore
from app.sampling_engine import SamplingEngine
from app.text_chunker import chunk_text

load_dotenv()

app = FastAPI(
    title="Kosuke Protocol",
    description="An Intelligence Ecosystem for Meaning Generation in the Age of AI",
    version="0.1.0",
)

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize stores and engines
fragment_store = FragmentStore(persist_directory="./chroma_data")
reflection_store = ReflectionStore(storage_path="./reflections.json")
edge_store = EdgeStore(storage_path="./edges.json")
sampling_engine = SamplingEngine(fragment_store)
slow_mode_tracker = SlowModeTracker()


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


# --- Fragment endpoints ---


@app.post("/fragments", response_model=Fragment)
async def create_fragment(fragment: FragmentCreate):
    """Add a single fragment to the ecosystem."""
    return fragment_store.add_fragment(fragment)


@app.post("/fragments/ingest", response_model=list[Fragment])
async def ingest_text(ingest: FragmentIngest):
    """Ingest a longer text, chunking it into fragments automatically."""
    chunks = chunk_text(ingest.text, ingest.chunk_size, ingest.chunk_overlap)
    if not chunks:
        raise HTTPException(status_code=400, detail="No fragments could be extracted from the text.")

    fragment_creates = [
        FragmentCreate(text=chunk, source=ingest.source, tags=ingest.tags, domain=ingest.domain)
        for chunk in chunks
    ]
    return fragment_store.add_fragments_bulk(fragment_creates)


@app.get("/fragments", response_model=list[Fragment])
async def list_fragments(limit: int = 100, offset: int = 0):
    """List all fragments with pagination."""
    return fragment_store.get_all_fragments(limit=limit, offset=offset)


@app.get("/fragments/count")
async def fragment_count():
    """Get the total number of fragments."""
    return {"count": fragment_store.count()}


@app.get("/fragments/{fragment_id}", response_model=Fragment)
async def get_fragment(fragment_id: str):
    """Get a single fragment by ID."""
    fragment = fragment_store.get_fragment(fragment_id)
    if not fragment:
        raise HTTPException(status_code=404, detail="Fragment not found")
    return fragment


@app.delete("/fragments/{fragment_id}")
async def delete_fragment(fragment_id: str):
    """Delete a fragment by ID."""
    success = fragment_store.delete_fragment(fragment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Fragment not found")
    return {"status": "deleted"}


# --- Sampling endpoints ---


@app.post("/sample", response_model=list[Fragment])
async def sample_fragments(request: SampleRequest):
    """Sample fragments using the specified method."""
    return sampling_engine.sample(
        method=request.method,
        query=request.query,
        tags=request.tags,
        n=request.n,
    )


# --- Fluke endpoints ---


@app.post("/fluke", response_model=FlukeResult)
async def generate_fluke_endpoint(request: FlukeRequest):
    """Generate a fluke - an unexpected conceptual connection between fragments.

    Uses domain-crossing prioritization (80%) and serendipity/random pairing (20%).
    Respects slow mode session limits.
    """
    session_id = request.session_id or "default"

    # Check slow mode limits
    if not slow_mode_tracker.can_generate(session_id):
        status = slow_mode_tracker.get_status(session_id)
        raise HTTPException(
            status_code=429,
            detail=status.message or "Slow mode limit reached. Take time to reflect.",
        )

    if fragment_store.count() < 2:
        raise HTTPException(
            status_code=400,
            detail="Need at least 2 fragments to generate a fluke. Add more fragments first.",
        )

    result = await generate_fluke(
        store=fragment_store,
        sampling_engine=sampling_engine,
        query=request.query,
        n_candidates=request.n_candidates,
    )

    if not result:
        raise HTTPException(status_code=500, detail="Could not generate a fluke. Try again.")

    # Record generation for slow mode tracking
    slow_mode_tracker.record_generation(session_id)

    # Create fluke edge in the network
    edge_store.create_fluke_edge(
        result.fragment_a.id,
        result.fragment_b.id,
        result.distance,
    )

    # Create domain-crossing edge if applicable
    if result.domain_crossing > 0:
        edge_store.create_domain_crossing_edge(
            result.fragment_a.id,
            result.fragment_b.id,
            result.domain_crossing,
        )

    return result


# --- Slow Mode endpoints ---


@app.get("/slow-mode/status", response_model=SlowModeStatus)
async def get_slow_mode_status(session_id: str = "default"):
    """Get the current slow mode status for a session."""
    return slow_mode_tracker.get_status(session_id)


@app.post("/slow-mode/reset", response_model=SlowModeStatus)
async def reset_slow_mode(session_id: str = "default"):
    """Reset the fluke count for a session."""
    slow_mode_tracker.reset_session(session_id)
    return slow_mode_tracker.get_status(session_id)


@app.put("/slow-mode/config", response_model=SlowModeConfig)
async def update_slow_mode_config(config: SlowModeConfig):
    """Update slow mode configuration."""
    slow_mode_tracker.update_config(config)
    return config


# --- Reflection endpoints ---


@app.post("/reflections", response_model=Reflection)
async def create_reflection(reflection: ReflectionCreate):
    """Save a reflection."""
    result = reflection_store.add_reflection(reflection)

    # Also store the reflection as a new fragment to feed back into the ecosystem
    reflection_fragment = fragment_store.add_fragment(
        FragmentCreate(
            text=reflection.text,
            source="reflection",
            tags=["reflection"],
        )
    )

    # Create reflection edges linking to the original fragments
    for frag_id in reflection.linked_fragment_ids:
        edge_store.create_reflection_edge(frag_id, reflection_fragment.id)

    return result


@app.get("/reflections", response_model=list[Reflection])
async def list_reflections(limit: int = 100, offset: int = 0):
    """List all reflections."""
    return reflection_store.get_all_reflections(limit=limit, offset=offset)


@app.get("/reflections/{reflection_id}", response_model=Reflection)
async def get_reflection(reflection_id: str):
    """Get a single reflection by ID."""
    reflection = reflection_store.get_reflection(reflection_id)
    if not reflection:
        raise HTTPException(status_code=404, detail="Reflection not found")
    return reflection


@app.delete("/reflections/{reflection_id}")
async def delete_reflection(reflection_id: str):
    """Delete a reflection by ID."""
    success = reflection_store.delete_reflection(reflection_id)
    if not success:
        raise HTTPException(status_code=404, detail="Reflection not found")
    return {"status": "deleted"}


# --- Export endpoints ---


@app.post("/export/markdown", response_class=PlainTextResponse)
async def export_markdown(request: ExportRequest):
    """Export the ecosystem as a markdown document (Living Book)."""
    lines: list[str] = []
    lines.append(f"# {request.title}")
    lines.append("")
    lines.append(f"*Generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*")
    lines.append("")
    lines.append("---")
    lines.append("")

    if request.include_fragments:
        fragments = fragment_store.get_all_fragments(limit=1000)
        if fragments:
            lines.append("## Fragments")
            lines.append("")
            for i, frag in enumerate(fragments, 1):
                lines.append(f"### Fragment {i}")
                lines.append("")
                lines.append(f"> {frag.text}")
                lines.append("")
                if frag.tags:
                    lines.append(f"*Tags: {', '.join(frag.tags)}*  ")
                lines.append(f"*Source: {frag.source} | {frag.timestamp}*")
                lines.append("")

    if request.include_reflections:
        reflections = reflection_store.get_all_reflections(limit=1000)
        if reflections:
            lines.append("## Reflections")
            lines.append("")
            for i, ref in enumerate(reflections, 1):
                lines.append(f"### Reflection {i}")
                lines.append("")
                lines.append(ref.text)
                lines.append("")
                if ref.linked_fluke_tension:
                    lines.append(f"*Fluke tension: {ref.linked_fluke_tension}*")
                lines.append(f"*Written: {ref.timestamp}*")
                lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Kosuke Protocol - An Intelligence Ecosystem for Meaning Generation*")

    return "\n".join(lines)


# --- Network endpoints ---


@app.get("/network", response_model=NetworkData)
async def get_network():
    """Get the full fragment network for visualization."""
    return edge_store.build_network(fragment_store)


@app.get("/network/metrics", response_model=NetworkMetrics)
async def get_network_metrics():
    """Get metrics about the fragment network."""
    return edge_store.get_metrics(fragment_store)


@app.post("/network/generate-edges")
async def generate_semantic_edges(threshold: float = 0.82):
    """Generate semantic similarity edges between fragments.

    This scans all fragment pairs and creates edges where
    cosine similarity exceeds the threshold.
    """
    new_edges = edge_store.generate_semantic_edges(
        fragment_store, similarity_threshold=threshold
    )
    return {
        "new_edges_created": len(new_edges),
        "total_edges": edge_store.count(),
    }


@app.post("/network/generate-gravity")
async def generate_gravity_edges(
    threshold: float = 0.5,
    epsilon: float = 0.01,
):
    """Generate gravity edges between fragments based on meaning mass.

    Gravity formula: gravity(A,B) = (mass_A * mass_B) / (distance^2 + epsilon)
    Fragments with high meaning mass attract each other across semantic space.
    """
    new_edges = edge_store.generate_gravity_edges(
        fragment_store,
        gravity_threshold=threshold,
        epsilon=epsilon,
    )
    return {
        "new_gravity_edges": len(new_edges),
        "total_edges": edge_store.count(),
    }


@app.post("/network/detect-galaxies", response_model=GalaxyData)
async def detect_galaxies(
    density_threshold: float = 0.3,
):
    """Detect clusters using Leiden algorithm and identify galaxies.

    A galaxy is a cluster with size >= 4 and density > threshold.
    Galaxy center = node with highest meaning_mass in the cluster.
    """
    return edge_store.detect_galaxies(
        fragment_store,
        density_threshold=density_threshold,
    )


@app.post("/network/drift", response_model=DriftAnalysis)
async def analyze_drift(
    mode: str = "monthly",
):
    """Analyze meaning drift across time slices.

    Tracks how gravity hubs, galaxies, and meaning structures
    evolve over time periods (monthly, quarterly, yearly).

    Classifies drift types:
    - emergence: new hubs appearing
    - migration: hubs shifting mass significantly
    - collapse: hubs disappearing
    - stable: hubs maintaining position
    """
    if mode not in ("monthly", "quarterly", "yearly"):
        raise HTTPException(
            status_code=400,
            detail="mode must be one of: monthly, quarterly, yearly",
        )
    return compute_drift(fragment_store, edge_store, mode=mode)


@app.get("/stats")
async def get_stats():
    """Get ecosystem statistics."""
    return {
        "fragments": fragment_store.count(),
        "reflections": reflection_store.count(),
        "edges": edge_store.count(),
    }
