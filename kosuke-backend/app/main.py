"""Kosuke Protocol - An Intelligence Ecosystem for Meaning Generation.

FastAPI backend providing fragment ingestion, vector memory,
sampling, fluke generation, reflection storage, and markdown export.
"""

import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.drift_engine import compute_drift
from app.edge_store import EdgeStore
from app.fluke_engine import SlowModeTracker, generate_fluke
from app.fragment_store import FragmentStore
from app.models import (
    CosmosData,
    DriftAnalysis,
    DomainBalanceResult,
    EmergingSignalsResult,
    ExperienceExportRequest,
    ExperienceFlukeRequest,
    ExperienceFragmentRequest,
    ExperienceFragmentResponse,
    ExperienceMeaningRequest,
    ExperienceMeaningResponse,
    ExperienceSampleRequest,
    ExperienceSampleResponse,
    ExportRequest,
    Fragment,
    FragmentCreate,
    FragmentIngest,
    FlukeRequest,
    FlukeResult,
    GalaxyData,
    GalaxyWatchResult,
    LensInfo,
    NetworkData,
    NetworkMetrics,
    ParallelLifeClarifyRequest,
    ParallelLifeClarifyResponse,
    ParallelLifeEditorialClarifyRequest,
    ParallelLifeEditorialRequest,
    ParallelLifeEditorialResponse,
    ParallelLifeExportRequest,
    ParallelLifeLensConfig,
    ParallelLifeRequest,
    ParallelLifeResult,
    Reflection,
    ReflectionCreate,
    ReflectionImpactResult,
    SampleRequest,
    SlowModeConfig,
    SlowModeStatus,
    TopConceptsResult,
)
from app.experience_engine import get_seed_fragments, generate_fragments, generate_meaning
from app.fluke_engine import compute_fluke_score, generate_tension_and_prompt
from app.lenses import LENSES, get_lens
from app.cosmos_engine import analyze_cosmos, list_authors
from app.parallel_life_engine import (
    export_parallel_life_markdown,
    generate_clarification_questions,
    generate_parallel_life,
)
from app.parallel_life_editorial import (
    generate_editorial_clarification_questions,
    generate_editorial_parallel_life,
)
from app.parallel_life_lens import get_parallel_life_lens_config
from app.observatory_engine import (
    get_domain_balance,
    get_emerging_signals,
    get_galaxy_watch,
    get_reflection_impact,
    get_top_concepts,
)
from app.reflection_store import ReflectionStore
from app.sampling_engine import SamplingEngine
from app.text_chunker import chunk_text

load_dotenv()

_logger = logging.getLogger("kosuke.observability")


def _cors_allow_origins() -> list[str]:
    raw = os.environ.get("CORS_ALLOW_ORIGINS", "").strip()
    if not raw:
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


def deep_reading_enabled() -> bool:
    return os.environ.get("DEEP_READING_ENABLED", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _require_deep_reading_enabled() -> None:
    if not deep_reading_enabled():
        raise HTTPException(
            status_code=503,
            detail="Deep Reading は現在メンテナンス中です。しばらくしてから再度お試しください。",
        )


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Lightweight request logging — no raw input / manuscript / prompts / keys."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        status_code = 500
        failure_category = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-Id"] = request_id
            if status_code >= 500:
                failure_category = "server_error"
            elif status_code >= 400:
                failure_category = "client_error"
            return response
        except Exception:
            failure_category = "unhandled_exception"
            raise
        finally:
            latency_ms = int((time.perf_counter() - started) * 1000)
            runtime_version = None
            try:
                from app.parallel_life_deep_reading import SCHEMA_VERSION

                runtime_version = SCHEMA_VERSION
            except Exception:
                runtime_version = None
            _logger.info(
                "request_id=%s method=%s path=%s status=%s latency_ms=%s "
                "runtime_version=%s env=%s failure_category=%s",
                request_id,
                request.method,
                request.url.path,
                status_code,
                latency_ms,
                runtime_version,
                os.environ.get("ENV", ""),
                failure_category,
            )


app = FastAPI(
    title="Kosuke Protocol",
    description="An Intelligence Ecosystem for Meaning Generation in the Age of AI",
    version="0.1.0",
)

app.add_middleware(ObservabilityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize stores and engines
fragment_store = FragmentStore(persist_directory="./chroma_data")
reflection_store = ReflectionStore(storage_path="./reflections.json")
edge_store = EdgeStore(storage_path="./edges.json")
sampling_engine = SamplingEngine(fragment_store)
slow_mode_tracker = SlowModeTracker()


@app.get("/healthz")
async def healthz():
    return {
        "status": "ok",
        "deep_reading_enabled": deep_reading_enabled(),
        "env": os.environ.get("ENV", ""),
    }


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
        FragmentCreate(text=chunk, source=ingest.source, tags=ingest.tags, domain=ingest.domain, author=ingest.author)
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


# --- Protocol Experience endpoints ---


def _lang_tag(language: str) -> str:
    return "lang:ja" if (language or "").lower().startswith("ja") else "lang:en"


_CJK_RE = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")


def _fragment_is_japanese(fragment: Fragment) -> bool:
    """Detect whether a fragment is Japanese via tag or content.

    Content detection makes this robust to legacy fragments that were stored
    before language tagging existed.
    """
    if "lang:ja" in fragment.tags:
        return True
    return bool(_CJK_RE.search(fragment.text))


def _language_pool(language: str, all_frags: list[Fragment]) -> list[Fragment]:
    """Return fragments that belong to the active language.

    A Japanese session only sees Japanese fragments; an English session only
    sees non-Japanese fragments. Both tag and content are checked so a session
    never receives a mixed-language counterpart.
    """
    if (language or "").lower().startswith("ja"):
        return [f for f in all_frags if _fragment_is_japanese(f)]
    return [f for f in all_frags if not _fragment_is_japanese(f)]


def _ensure_seed_corpus(language: str) -> None:
    """Seed a small curated corpus in the active language if the language pool
    is nearly empty. Keeps the experience usable (and single-language) on a
    fresh install.
    """
    pool = _language_pool(language, fragment_store.get_all_fragments(limit=1000))
    if len(pool) >= 4:
        return
    lang_tag = _lang_tag(language)
    for seed in get_seed_fragments(language):
        fragment_store.add_fragment(
            FragmentCreate(
                text=seed["text"],
                source="seed",
                tags=["seed", "experience", lang_tag],
                domain=seed.get("domain"),
            )
        )


def _select_from_pool(
    mode: str, selected: Fragment, pool: list[Fragment]
) -> Fragment | None:
    """Select one counterpart from a language-scoped pool, per sampling mode.

    Reuses the sampling engine's cosine distance and fragment embeddings so no
    sampling logic is duplicated; only the human-readable mode mapping and the
    language scoping live here.
    """
    import random

    if not pool:
        return None

    if mode in ("near", "far"):
        ids = [selected.id] + [f.id for f in pool]
        embeddings = fragment_store.get_embeddings(ids)
        base = embeddings.get(selected.id)
        if base:
            best: Fragment | None = None
            best_dist = -1.0 if mode == "far" else 2.0
            for frag in pool:
                emb = embeddings.get(frag.id)
                if not emb:
                    continue
                dist = sampling_engine._cosine_distance(base, emb)
                if (mode == "far" and dist > best_dist) or (
                    mode == "near" and dist < best_dist
                ):
                    best_dist = dist
                    best = frag
            if best is not None:
                return best
        return random.choice(pool)

    if mode == "time":
        try:
            ordered = sorted(pool, key=lambda f: f.timestamp, reverse=True)
        except Exception:
            ordered = pool
        # Favor a recent-but-not-identical fragment.
        return ordered[0]

    # chance (and any unknown mode)
    return random.choice(pool)


def _lens_infos() -> list[LensInfo]:
    return [
        LensInfo(
            id=lens.id,
            name_en=lens.name_en,
            name_ja=lens.name_ja,
            description_en=lens.description_en,
            description_ja=lens.description_ja,
            available=lens.available,
        )
        for lens in LENSES.values()
    ]


@app.get("/experience/lenses", response_model=list[LensInfo])
async def experience_lenses():
    """List available and upcoming lenses for the experience."""
    return _lens_infos()


@app.post("/experience/fragment", response_model=ExperienceFragmentResponse)
async def experience_fragment(request: ExperienceFragmentRequest):
    """Transform raw user input into 4-7 minimal thought units."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Please write something first.")

    lens = get_lens(request.lens)
    fragments = await generate_fragments(
        text=request.text,
        language=request.language,
        lens_id=lens.id,
    )
    return ExperienceFragmentResponse(
        source_text=request.text,
        fragments=fragments,
        language=request.language,
        lens=lens.id,
    )


@app.post("/experience/sample", response_model=ExperienceSampleResponse)
async def experience_sample(request: ExperienceSampleRequest):
    """Sample a counterpart fragment from the ecosystem for the selected fragment.

    Human-readable modes map onto the existing sampling engine:
    near -> semantic, far -> semantic-distance, time -> temporal, chance -> random.
    """
    if not request.fragment_text.strip():
        raise HTTPException(status_code=400, detail="Select a fragment to explore first.")

    lens = get_lens(request.lens)
    language = request.language

    # Persist the selected fragment so it gains an embedding and joins the
    # living ecosystem. It is tagged with the active language so future
    # sampling stays single-language. This also lets the fluke engine compute
    # a real semantic distance.
    selected = fragment_store.add_fragment(
        FragmentCreate(
            text=request.fragment_text,
            source="experience",
            tags=["experience", lens.id, _lang_tag(language)],
        )
    )

    _ensure_seed_corpus(language)

    exclude = set(request.exclude_ids) | {selected.id}
    mode = request.mode.lower()
    mode_to_method = {
        "near": "semantic",
        "far": "semantic-distance",
        "time": "temporal",
        "chance": "random",
    }
    method = mode_to_method.get(mode, "random")

    # Build the language-scoped candidate pool (never mixes languages).
    all_frags = fragment_store.get_all_fragments(limit=1000)
    pool = [
        f
        for f in _language_pool(language, all_frags)
        if f.id not in exclude
    ]

    sampled: Fragment | None = _select_from_pool(
        mode, selected, pool
    )

    if sampled is None:
        raise HTTPException(
            status_code=409,
            detail="Not enough fragments to sample from yet. Please try again.",
        )

    return ExperienceSampleResponse(
        selected_fragment=selected,
        sampled_fragment=sampled,
        mode=mode,
        method=method,
    )


@app.post("/experience/fluke", response_model=FlukeResult)
async def experience_fluke(request: ExperienceFlukeRequest):
    """Generate a fluke connection between two specific fragments."""
    frag_a = request.original_fragment
    frag_b = request.sampled_fragment

    # Ensure the original fragment exists in the store so distance is meaningful.
    if not frag_a.id or not fragment_store.get_fragment(frag_a.id):
        frag_a = fragment_store.add_fragment(
            FragmentCreate(
                text=frag_a.text,
                source="experience",
                tags=["experience", _lang_tag(request.language)],
            )
        )

    query = request.query or frag_a.text
    scores = compute_fluke_score(fragment_store, frag_a, frag_b, query)
    tension, reflection_prompt = await generate_tension_and_prompt(
        frag_a, frag_b, query, request.language
    )

    # Record the connection in the network (best-effort).
    try:
        edge_store.create_fluke_edge(frag_a.id, frag_b.id, scores["distance"])
        if scores["domain_crossing"] > 0:
            edge_store.create_domain_crossing_edge(
                frag_a.id, frag_b.id, scores["domain_crossing"]
            )
    except Exception:
        pass

    return FlukeResult(
        fragment_a=frag_a,
        fragment_b=frag_b,
        distance=scores["distance"],
        core_resonance=scores["core_resonance"],
        tension_score=scores["tension_score"],
        context_fit=scores["context_fit"],
        domain_crossing=scores["domain_crossing"],
        fluke_score=scores["fluke_score"],
        tension=tension,
        reflection_prompt=reflection_prompt,
        generation_method="experience",
    )


@app.post("/experience/meaning", response_model=ExperienceMeaningResponse)
async def experience_meaning(request: ExperienceMeaningRequest):
    """Generate a concise emergent meaning that builds on the user's reflection."""
    lens = get_lens(request.lens)
    meaning = await generate_meaning(
        source_text=request.source_text,
        original_text=request.original_fragment.text,
        sampled_text=request.sampled_fragment.text,
        tension=request.fluke.tension,
        reflection=request.reflection,
        language=request.language,
        lens_id=lens.id,
    )
    return ExperienceMeaningResponse(meaning=meaning)


@app.post("/experience/export", response_class=PlainTextResponse)
async def experience_export(request: ExperienceExportRequest):
    """Export a single Meaning Card as a clean Living Book markdown entry."""
    created = request.created_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    title = request.title or "Kosuke Protocol - Meaning Card"

    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"*{created}*")
    if request.sampling_mode:
        lines.append(f"*Sampling mode: {request.sampling_mode}*")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Source")
    lines.append("")
    lines.append(f"> {request.source_text}")
    lines.append("")
    lines.append("## Connection")
    lines.append("")
    lines.append(f"- **Fragment:** {request.original_fragment_text}")
    lines.append(f"- **Sampled:** {request.sampled_fragment_text}")
    lines.append("")
    if request.tension:
        lines.append("## Tension")
        lines.append("")
        lines.append(request.tension)
        lines.append("")
    if request.reflection_question:
        lines.append("## Question")
        lines.append("")
        lines.append(f"*{request.reflection_question}*")
        lines.append("")
    if request.reflection:
        lines.append("## Reflection")
        lines.append("")
        lines.append(request.reflection)
        lines.append("")
    if request.meaning:
        lines.append("## Meaning")
        lines.append("")
        lines.append(f"**{request.meaning}**")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Kosuke Protocol - Protocol Experience*")

    return "\n".join(lines)


# --- Parallel Life endpoints ---
#
# Parallel Life is the first primary public experience of Kosuke Protocol. It
# reuses the same LLM + heuristic fallback pattern as the rest of the
# experience, but is a self-contained structured-generation flow: it does not
# read from or write to the fragment ecosystem (FragmentStore / ChromaDB), and
# it does not use the six-stage Fragment/Sample/Fluke/Reflection/Meaning loop.


@app.get("/experience/parallel-life/lens", response_model=ParallelLifeLensConfig)
async def parallel_life_lens():
    """Return the typed Parallel Life lens configuration for the frontend."""
    return get_parallel_life_lens_config()


@app.post("/experience/parallel-life/clarify", response_model=ParallelLifeClarifyResponse)
async def parallel_life_clarify(request: ParallelLifeClarifyRequest):
    """Return 0-4 optional clarification questions for a written life branch."""
    if not request.source_text.strip():
        raise HTTPException(status_code=400, detail="Please write the branch first.")
    questions = await generate_clarification_questions(request.source_text, request.language)
    return ParallelLifeClarifyResponse(questions=questions, language=request.language)


@app.post("/experience/parallel-life", response_model=ParallelLifeResult)
async def parallel_life_generate(request: ParallelLifeRequest):
    """Generate a structured Parallel Life reading from a written life branch.

    Standard depth: LLM with heuristic fallback.
    Editorial / legacy deep: LLM-required book-style essay (no heuristic fallback).
    """
    from app.parallel_life_editorial_essay import (
        EditorialGenerationError,
        EditorialLLMRequiredError,
    )

    if not request.source_text.strip():
        raise HTTPException(status_code=400, detail="Please write the branch first.")
    try:
        return await generate_parallel_life(request)
    except EditorialLLMRequiredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except EditorialGenerationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="The reading could not be completed. Your input has been preserved. Please try again.",
        )


@app.post("/experience/parallel-life/export", response_class=PlainTextResponse)
async def parallel_life_export(request: ParallelLifeExportRequest):
    """Export a Parallel Life reading as clean, publishable Markdown."""
    return export_parallel_life_markdown(request.result, request.created_at)


@app.post(
    "/experience/parallel-life/editorial/clarify",
    response_model=ParallelLifeClarifyResponse,
)
async def parallel_life_editorial_clarify(request: ParallelLifeEditorialClarifyRequest):
    """Return up to 5 optional Editorial Edition preparation questions."""
    if not request.source_text.strip():
        raise HTTPException(status_code=400, detail="Please write the branch first.")
    questions = generate_editorial_clarification_questions(
        request.source_text,
        request.language,
        request.clarifications,
        request.answered_editorial_ids,
    )
    return ParallelLifeClarifyResponse(questions=questions, language=request.language)


@app.post(
    "/experience/parallel-life/editorial",
    response_model=ParallelLifeEditorialResponse,
)
async def parallel_life_editorial_generate(request: ParallelLifeEditorialRequest):
    """Generate the Editorial Edition (depth=editorial) from a life branch.

    LLM-required book-style single essay. No heuristic fallback — on failure
    the session is preserved and the client may retry.
    """
    from app.parallel_life_editorial_essay import (
        EditorialGenerationError,
        EditorialLLMRequiredError,
    )

    if not request.source_text.strip():
        raise HTTPException(status_code=400, detail="Please write the branch first.")
    try:
        return await generate_editorial_parallel_life(request)
    except EditorialLLMRequiredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except EditorialGenerationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="編集版を生成できませんでした。入力は保存されています。もう一度お試しください。",
        )


# --- Deep Reading Production Candidate v1.0 (Call 1 / 2 / 3) ---
# Separate from Standard and legacy Editorial Edition. No heuristic long-form
# fallback. Session state is server-side; do not rely on localStorage alone.


@app.get("/experience/parallel-life/deep-reading/enabled")
async def deep_reading_enabled_endpoint():
    """Kill-switch probe for frontend CTA visibility (+ v1.1 Context Pack flag)."""
    from app.parallel_life_deep_reading.context_pack import context_pack_feature_enabled

    return {
        "enabled": deep_reading_enabled(),
        "context_pack_enabled": bool(
            deep_reading_enabled() and context_pack_feature_enabled()
        ),
    }


@app.post("/experience/parallel-life/deep-reading/context-pack/seed")
async def deep_reading_context_pack_seed(request: dict):
    """Deterministic extractive Context Pack draft (v1.1-exp). Never invents biography."""
    _require_deep_reading_enabled()
    from app.parallel_life_deep_reading.context_pack import (
        context_pack_feature_enabled,
        seed_context_pack_from_text,
    )

    if not context_pack_feature_enabled():
        raise HTTPException(status_code=404, detail="context_pack_disabled")
    text = str(request.get("text") or "").strip()
    language = str(request.get("language") or "ja")
    source = str(request.get("source") or "session_seeded_draft")
    if source not in {"session_seeded_draft", "imported_paste"}:
        source = "session_seeded_draft"
    pack = seed_context_pack_from_text(text, language=language, source=source)  # type: ignore[arg-type]
    return {"context_pack": pack.model_dump(mode="json")}


@app.post("/experience/parallel-life/deep-reading/ground")
async def deep_reading_ground(request: dict):
    """Call 1: grounding and editorial design → user confirmation."""
    _require_deep_reading_enabled()
    from app.parallel_life_deep_reading.llm import (
        DeepReadingGenerationError,
        DeepReadingLLMRequiredError,
    )
    from app.parallel_life_deep_reading.models import DeepReadingGroundRequest
    from app.parallel_life_deep_reading.service import get_deep_reading_service

    payload = DeepReadingGroundRequest.model_validate(request)
    if not payload.source_text.strip():
        raise HTTPException(status_code=400, detail="Please write the branch first.")
    try:
        return get_deep_reading_service().ground(payload)
    except DeepReadingLLMRequiredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DeepReadingGenerationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/experience/parallel-life/deep-reading/confirm")
async def deep_reading_confirm(request: dict):
    """User confirmation / edit / answer / abort for grounded_input."""
    _require_deep_reading_enabled()
    from app.parallel_life_deep_reading.llm import DeepReadingGenerationError
    from app.parallel_life_deep_reading.models import DeepReadingConfirmRequest
    from app.parallel_life_deep_reading.service import get_deep_reading_service

    payload = DeepReadingConfirmRequest.model_validate(request)
    try:
        return get_deep_reading_service().confirm(payload)
    except KeyError:
        raise HTTPException(status_code=404, detail="Deep Reading session not found.")
    except DeepReadingGenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/experience/parallel-life/deep-reading/draft")
async def deep_reading_draft(request: dict):
    """Call 2: single-manuscript draft (requires confirmed grounded_input)."""
    _require_deep_reading_enabled()
    from app.parallel_life_deep_reading.llm import (
        DeepReadingGenerationError,
        DeepReadingLLMRequiredError,
    )
    from app.parallel_life_deep_reading.models import DeepReadingDraftRequest
    from app.parallel_life_deep_reading.service import get_deep_reading_service

    payload = DeepReadingDraftRequest.model_validate(request)
    try:
        return get_deep_reading_service().draft(
            payload.session_id,
            idempotency_key=payload.idempotency_key,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Deep Reading session not found.")
    except DeepReadingLLMRequiredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DeepReadingGenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/experience/parallel-life/deep-reading/edit-validate")
async def deep_reading_edit_validate(request: dict):
    """Call 3: whole-document edit and runtime validation gate."""
    _require_deep_reading_enabled()
    from app.parallel_life_deep_reading.llm import (
        DeepReadingGenerationError,
        DeepReadingLLMRequiredError,
    )
    from app.parallel_life_deep_reading.models import DeepReadingEditValidateRequest
    from app.parallel_life_deep_reading.service import get_deep_reading_service

    payload = DeepReadingEditValidateRequest.model_validate(request)
    try:
        return get_deep_reading_service().edit_validate(
            payload.session_id,
            idempotency_key=payload.idempotency_key,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Deep Reading session not found.")
    except DeepReadingLLMRequiredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DeepReadingGenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/experience/parallel-life/deep-reading/session/{session_id}")
async def deep_reading_session(session_id: str):
    """Fetch Deep Reading session state (server-side)."""
    _require_deep_reading_enabled()
    from app.parallel_life_deep_reading.service import get_deep_reading_service

    try:
        return get_deep_reading_service().get_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Deep Reading session not found.")


@app.post("/experience/parallel-life/deep-reading/regenerate")
async def deep_reading_regenerate(request: dict):
    """Retry from ground / draft / edit-validate without heuristic fallback."""
    _require_deep_reading_enabled()
    from app.parallel_life_deep_reading.llm import (
        DeepReadingGenerationError,
        DeepReadingLLMRequiredError,
    )
    from app.parallel_life_deep_reading.models import DeepReadingRegenerateRequest
    from app.parallel_life_deep_reading.service import get_deep_reading_service

    payload = DeepReadingRegenerateRequest.model_validate(request)
    try:
        return get_deep_reading_service().regenerate(
            payload.session_id, from_stage=payload.from_stage
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Deep Reading session not found.")
    except DeepReadingLLMRequiredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DeepReadingGenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/experience/parallel-life/deep-reading/export", response_class=PlainTextResponse)
async def deep_reading_export(request: dict):
    """Export completed Deep Reading manuscript as Markdown."""
    _require_deep_reading_enabled()
    from app.parallel_life_deep_reading.llm import DeepReadingGenerationError
    from app.parallel_life_deep_reading.models import DeepReadingExportRequest
    from app.parallel_life_deep_reading.service import get_deep_reading_service

    payload = DeepReadingExportRequest.model_validate(request)
    try:
        return get_deep_reading_service().export(
            payload.session_id,
            include_diagnostics=payload.include_diagnostics,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Deep Reading session not found.")
    except DeepReadingGenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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


# --- Observatory endpoints ---


@app.get("/observatory/top-concepts", response_model=TopConceptsResult)
async def observatory_top_concepts(limit: int = 20):
    """Rank fragments by meaning_mass and show trends over time."""
    return get_top_concepts(fragment_store, edge_store, limit=limit)


@app.get("/observatory/galaxies", response_model=GalaxyWatchResult)
async def observatory_galaxies():
    """List detected galaxies with size, density, center, and growth."""
    return get_galaxy_watch(fragment_store, edge_store)


@app.get("/observatory/reflection-impact", response_model=ReflectionImpactResult)
async def observatory_reflection_impact():
    """Measure structural impact of each reflection."""
    return get_reflection_impact(fragment_store, edge_store, reflection_store)


@app.get("/observatory/domain-balance", response_model=DomainBalanceResult)
async def observatory_domain_balance():
    """Visualize domain distribution and highlight imbalances."""
    return get_domain_balance(fragment_store, edge_store)


@app.get("/observatory/emerging-signals", response_model=EmergingSignalsResult)
async def observatory_emerging_signals(limit: int = 20):
    """Detect fragments with rising meaning_mass."""
    return get_emerging_signals(fragment_store, edge_store, limit=limit)


# --- Cosmos endpoints ---


@app.get("/cosmos", response_model=CosmosData)
async def get_cosmos(similarity_threshold: float = 0.75):
    """Analyze the collective cosmos across all authors.

    Returns author stats, cross-cosmos edges, shared galaxies,
    and collective gravity hubs.
    """
    return analyze_cosmos(fragment_store, edge_store, similarity_threshold)


@app.get("/cosmos/authors")
async def get_cosmos_authors():
    """List all unique authors in the ecosystem."""
    return {"authors": list_authors(fragment_store)}


@app.get("/stats")
async def get_stats():
    """Get ecosystem statistics."""
    return {
        "fragments": fragment_store.count(),
        "reflections": reflection_store.count(),
        "edges": edge_store.count(),
    }
