"""Pydantic models for Kosuke Protocol."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# Predefined domains for boundary-crossing fluke generation
DOMAINS = [
    "philosophy",
    "technology",
    "art",
    "science",
    "urban",
    "body",
    "nature",
    "politics",
    "economics",
    "culture",
    "psychology",
    "literature",
    "music",
    "spirituality",
    "mathematics",
]


class FragmentCreate(BaseModel):
    """Input model for creating a fragment."""

    text: str
    source: str = "manual"
    tags: list[str] = Field(default_factory=list)
    domain: Optional[str] = None  # domain tag for boundary-crossing flukes
    author: Optional[str] = None  # author for multi-user cosmos


class Fragment(BaseModel):
    """A minimal unit of thought."""

    id: str
    text: str
    source: str
    timestamp: str
    tags: list[str] = Field(default_factory=list)
    domain: Optional[str] = None  # domain tag for boundary-crossing flukes
    author: Optional[str] = None  # author for multi-user cosmos


class FragmentIngest(BaseModel):
    """Input model for ingesting text that will be chunked into fragments."""

    text: str
    source: str = "manual"
    tags: list[str] = Field(default_factory=list)
    domain: Optional[str] = None  # domain tag for boundary-crossing flukes
    author: Optional[str] = None  # author for multi-user cosmos
    chunk_size: int = 300
    chunk_overlap: int = 50


class SampleRequest(BaseModel):
    """Request model for sampling fragments."""

    method: str = "random"  # random, semantic, thematic, temporal
    query: Optional[str] = None  # for semantic sampling
    tags: list[str] = Field(default_factory=list)  # for thematic sampling
    n: int = 5


class FlukeRequest(BaseModel):
    """Request model for generating a fluke."""

    query: Optional[str] = None  # optional context for ContextFit
    n_candidates: int = 10  # number of candidate fragments to consider
    session_id: Optional[str] = None  # session ID for slow mode tracking


class FlukeResult(BaseModel):
    """Output model for a generated fluke."""

    fragment_a: Fragment
    fragment_b: Fragment
    distance: float
    core_resonance: float
    tension_score: float
    context_fit: float
    domain_crossing: float  # bonus score for cross-domain pairing
    fluke_score: float
    tension: str
    reflection_prompt: str
    generation_method: str = "standard"  # standard, serendipity, domain_cross


class ReflectionCreate(BaseModel):
    """Input model for creating a reflection."""

    text: str
    linked_fragment_ids: list[str] = Field(default_factory=list)
    linked_fluke_tension: Optional[str] = None


class Reflection(BaseModel):
    """A human reflection on a fluke or fragment."""

    id: str
    text: str
    linked_fragment_ids: list[str] = Field(default_factory=list)
    linked_fluke_tension: Optional[str] = None
    timestamp: str


class SlowModeConfig(BaseModel):
    """Configuration for slow mode - limits fluke generation per session."""

    enabled: bool = True
    max_flukes_per_session: int = 5
    cooldown_message: str = "Take time to reflect on the connections you've seen before generating more."


class SlowModeStatus(BaseModel):
    """Status of slow mode for the current session."""

    enabled: bool
    flukes_remaining: int
    flukes_generated: int
    max_flukes: int
    cooldown_active: bool
    message: Optional[str] = None


class FragmentEdge(BaseModel):
    """An edge between two fragments in the network."""

    id: str
    fragment_a: str  # fragment ID
    fragment_b: str  # fragment ID
    relation_type: str  # fluke, semantic_similarity, reflection_link, domain_crossing
    weight: float
    created_at: str


class ClusterInfo(BaseModel):
    """Information about a detected cluster."""

    cluster_id: int
    size: int
    density: float
    domain_entropy: float
    center_fragment: str  # fragment ID with highest meaning_mass
    is_galaxy: bool = False  # True if size >= 4 and density > threshold
    member_ids: list[str] = Field(default_factory=list)


class NetworkNode(BaseModel):
    """A node in the fragment network."""

    id: str
    text: str
    domain: Optional[str] = None
    author: Optional[str] = None
    type: str = "fragment"  # fragment, reflection
    is_boundary: bool = False
    meaning_mass: float = 0.0
    is_gravity_hub: bool = False
    cluster_id: Optional[int] = None
    is_galaxy_center: bool = False


class NetworkEdge(BaseModel):
    """An edge in the fragment network for visualization."""

    source: str
    target: str
    weight: float
    relation: str


class NetworkData(BaseModel):
    """Full network data for visualization."""

    nodes: list[NetworkNode]
    edges: list[NetworkEdge]


class NetworkMetrics(BaseModel):
    """Metrics about the fragment network."""

    fragments: int
    edges: int
    clusters: int
    boundary_nodes: int
    gravity_hubs: int = 0
    galaxy_count: int = 0
    largest_galaxy: int = 0
    average_cluster_size: float = 0.0


class GalaxyData(BaseModel):
    """Result of galaxy detection."""

    clusters: list[ClusterInfo]
    galaxies: list[ClusterInfo]
    galaxy_count: int
    largest_galaxy: int
    average_cluster_size: float


class TimeSliceMetrics(BaseModel):
    """Metrics for a single time slice."""

    slice_label: str  # e.g. "2025-01", "2025-Q1", "2025"
    start_time: str  # ISO timestamp
    end_time: str  # ISO timestamp
    fragment_count: int
    edge_count: int
    cluster_count: int
    galaxy_count: int
    gravity_hub_count: int
    hub_ids: list[str] = Field(default_factory=list)
    galaxy_centers: list[str] = Field(default_factory=list)
    meaning_mass_map: dict[str, float] = Field(default_factory=dict)


class DriftVector(BaseModel):
    """Tracks movement of a hub between two time slices."""

    fragment_id: str
    fragment_text: str
    domain: Optional[str] = None
    mass_t1: float
    mass_t2: float
    mass_delta: float  # mass_t2 - mass_t1
    was_hub_t1: bool
    is_hub_t2: bool
    drift_type: str  # emergence, migration, collapse, stable


class DriftAnalysis(BaseModel):
    """Full drift analysis across time slices."""

    slices: list[TimeSliceMetrics]
    drift_vectors: list[DriftVector]
    emergence_count: int  # new hubs appearing
    migration_count: int  # hubs shifting mass
    collapse_count: int  # hubs disappearing
    stable_count: int  # hubs remaining stable
    slice_mode: str  # monthly, quarterly, yearly


class TopConcept(BaseModel):
    """A fragment ranked by meaning_mass."""

    fragment_id: str
    text: str
    domain: Optional[str] = None
    meaning_mass: float
    is_gravity_hub: bool = False
    is_galaxy_center: bool = False
    edge_count: int = 0
    mass_trend: float = 0.0  # change vs previous slice


class TopConceptsResult(BaseModel):
    """Result of top concepts ranking."""

    concepts: list[TopConcept]
    total_fragments: int


class GalaxyWatch(BaseModel):
    """Observatory view of a single galaxy."""

    cluster_id: int
    size: int
    density: float
    domain_entropy: float
    center_fragment_id: str
    center_fragment_text: str
    center_domain: Optional[str] = None
    member_domains: list[str] = Field(default_factory=list)
    growth: int = 0  # size change vs previous slice (positive=growing)


class GalaxyWatchResult(BaseModel):
    """Result of galaxy watch."""

    galaxies: list[GalaxyWatch]
    total_galaxies: int


class ReflectionImpact(BaseModel):
    """Structural impact of a single reflection."""

    reflection_id: str
    reflection_text: str
    timestamp: str
    linked_fragment_count: int
    edges_created: int  # reflection_link edges from this reflection
    mass_boost: float  # total mass increase for linked fragments
    clusters_touched: int  # how many clusters the linked fragments span
    galaxies_touched: int  # how many galaxies the linked fragments belong to


class ReflectionImpactResult(BaseModel):
    """Result of reflection impact analysis."""

    reflections: list[ReflectionImpact]
    total_reflections: int
    avg_edges_created: float
    avg_mass_boost: float


class DomainStat(BaseModel):
    """Statistics for a single domain."""

    domain: str
    fragment_count: int
    percentage: float
    edge_count: int
    avg_meaning_mass: float
    hub_count: int


class DomainBalanceResult(BaseModel):
    """Result of domain balance analysis."""

    domains: list[DomainStat]
    total_fragments: int
    underrepresented: list[str] = Field(default_factory=list)
    dominant: list[str] = Field(default_factory=list)


class EmergingSignal(BaseModel):
    """A fragment with rising meaning_mass."""

    fragment_id: str
    text: str
    domain: Optional[str] = None
    current_mass: float
    mass_change: float  # positive = rising
    is_domain_crossing: bool = False
    is_reflection_linked: bool = False
    signal_strength: float = 0.0  # composite signal score


class EmergingSignalsResult(BaseModel):
    """Result of emerging signals detection."""

    signals: list[EmergingSignal]
    total_signals: int


# --- Cosmos models ---


class CosmosAuthor(BaseModel):
    """An author in the collective cosmos."""

    name: str
    fragment_count: int
    edge_count: int
    gravity_hub_count: int = 0
    galaxy_count: int = 0
    avg_meaning_mass: float = 0.0


class CrossCosmosEdge(BaseModel):
    """An edge connecting fragments from different authors."""

    fragment_a_id: str
    fragment_a_text: str
    fragment_a_author: str
    fragment_b_id: str
    fragment_b_text: str
    fragment_b_author: str
    similarity: float
    relation_type: str


class SharedGalaxy(BaseModel):
    """A galaxy containing fragments from multiple authors."""

    cluster_id: int
    size: int
    density: float
    authors: list[str] = Field(default_factory=list)
    author_counts: dict[str, int] = Field(default_factory=dict)
    center_fragment_id: str
    center_fragment_text: str
    center_author: Optional[str] = None
    domain_entropy: float = 0.0


class CollectiveHub(BaseModel):
    """A gravity hub computed across all authors."""

    fragment_id: str
    text: str
    author: Optional[str] = None
    domain: Optional[str] = None
    meaning_mass: float
    edge_count: int = 0
    cross_author_edges: int = 0


class CosmosData(BaseModel):
    """Full collective cosmos analysis."""

    authors: list[CosmosAuthor]
    cross_cosmos_edges: list[CrossCosmosEdge]
    shared_galaxies: list[SharedGalaxy]
    collective_hubs: list[CollectiveHub]
    total_fragments: int
    total_authors: int
    total_cross_edges: int
    total_shared_galaxies: int


class ExportRequest(BaseModel):
    """Request model for exporting as markdown."""

    title: str = "Kosuke Protocol - Living Book"
    include_fragments: bool = True
    include_reflections: bool = True
    include_flukes: bool = False


# --- Protocol Experience models ---


class ExperienceFragment(BaseModel):
    """A minimal thought unit generated for the guided experience."""

    id: str
    text: str
    type: str  # explicit | inferred | theme


class ExperienceFragmentRequest(BaseModel):
    """Request to transform raw input into experience fragments."""

    text: str
    language: str = "en"  # "ja" | "en"
    lens: str = "open"


class ExperienceFragmentResponse(BaseModel):
    """Generated experience fragments for a source text."""

    source_text: str
    fragments: list[ExperienceFragment]
    language: str
    lens: str


class ExperienceSampleRequest(BaseModel):
    """Request to sample a counterpart fragment from the ecosystem."""

    fragment_text: str
    mode: str = "chance"  # near | far | time | chance
    language: str = "en"
    lens: str = "open"
    exclude_ids: list[str] = Field(default_factory=list)


class ExperienceSampleResponse(BaseModel):
    """A sampled counterpart placed opposite the user's fragment."""

    selected_fragment: Fragment
    sampled_fragment: Fragment
    mode: str
    method: str  # internal sampling method used


class ExperienceFlukeRequest(BaseModel):
    """Request to generate a fluke between two specific fragments."""

    original_fragment: Fragment
    sampled_fragment: Fragment
    query: Optional[str] = None
    language: str = "en"


class ExperienceMeaningRequest(BaseModel):
    """Request to generate a concise emergent meaning for a session."""

    source_text: str
    original_fragment: Fragment
    sampled_fragment: Fragment
    fluke: FlukeResult
    reflection: str = ""
    language: str = "en"
    lens: str = "open"


class ExperienceMeaningResponse(BaseModel):
    """A concise, one-line emergent meaning."""

    meaning: str


class ExperienceExportRequest(BaseModel):
    """Request to export a single Meaning Card as a Living Book entry."""

    source_text: str
    original_fragment_text: str
    sampled_fragment_text: str
    tension: str = ""
    reflection_question: str = ""
    reflection: str = ""
    meaning: str = ""
    sampling_mode: str = ""
    language: str = "en"
    created_at: Optional[str] = None
    title: Optional[str] = None


class LensInfo(BaseModel):
    """Public description of a lens for the experience UI."""

    id: str
    name_en: str
    name_ja: str
    description_en: str
    description_ja: str
    available: bool


# --- Parallel Life models ---
#
# Parallel Life is the first primary public experience of Kosuke Protocol. It
# reuses the same engines (LLM + heuristic fallback, language safeguards, seed
# corpus pattern) but exposes a narrative "life branch" reading instead of the
# generic six-stage protocol flow. The internal protocol mechanics stay active
# but invisible.

ParallelLifeDepth = str  # "standard" | "editorial" (legacy alias: "deep" → "editorial")
ParallelLifeLanguage = str  # "ja" | "en"


class ParallelLifeClarifications(BaseModel):
    """Optional clarification answers. Every field is optional by design; the
    user is never forced to disclose sensitive information."""

    age: Optional[str] = None
    chosen_path: Optional[str] = None
    unchosen_path: Optional[str] = None
    what_remains: Optional[str] = None
    constraints: Optional[str] = None
    lost: Optional[str] = None
    protected: Optional[str] = None


class ParallelLifeRequest(BaseModel):
    """Request to generate a Parallel Life reading from a life branch."""

    source_text: str
    clarifications: ParallelLifeClarifications = Field(
        default_factory=ParallelLifeClarifications
    )
    language: str = "ja"  # "ja" | "en"
    depth: str = "standard"  # "standard" | "editorial" (alias: "deep")


class ObservatoryLayer(BaseModel):
    """A single observatory-lens reading of the personal branch.

    ``title`` is always the official lens name (kept in English in both
    languages, e.g. "Market Signals" — never translated or transliterated
    inconsistently). ``descriptor`` is a short, concrete phrase in the
    response language shown directly beneath the name (e.g. "生活を成立させ
    る市場条件"), distinct from the longer free-text ``body`` reading.
    """

    id: str  # one of the enumerated ObservatoryLensId values
    title: str
    descriptor: str = ""
    body: str


class ParallelLifeResult(BaseModel):
    """The structured Parallel Life document."""

    title: str
    subtitle: str
    branch_point: str
    chosen_path: str
    unchosen_life: str
    lost: list[str] = Field(default_factory=list)
    protected: list[str] = Field(default_factory=list)
    residue: str
    observatory_layers: list[ObservatoryLayer] = Field(default_factory=list)
    cross_lens_synthesis: str
    rebranch: list[str] = Field(default_factory=list)
    closing: str
    generation_mode: str = "heuristic"  # "llm" | "heuristic"
    language: str = "ja"
    depth: str = "standard"


class ObservatoryLensInfo(BaseModel):
    """Public description of an observatory lens."""

    id: str
    name_en: str
    name_ja: str
    description_en: str
    description_ja: str


class ParallelLifeLensConfig(BaseModel):
    """Typed configuration for the Parallel Life lens, consumed by the frontend
    so Parallel Life logic is not hardcoded in the UI."""

    id: str
    name: str  # official product name (kept in English)
    name_ja: str
    description_en: str
    description_ja: str
    available: bool
    entry_prompts_en: dict[str, str]
    entry_prompts_ja: dict[str, str]
    supported_depths: list[str]
    observatory_lenses: list[ObservatoryLensInfo]
    seed_corpus_id: str


class ClarificationQuestion(BaseModel):
    """A single optional clarification question."""

    id: str
    question: str


class ParallelLifeClarifyRequest(BaseModel):
    """Request to derive optional clarification questions for a branch."""

    source_text: str
    language: str = "ja"


class ParallelLifeClarifyResponse(BaseModel):
    """Optional clarification questions (0-4). Answers are never required."""

    questions: list[ClarificationQuestion] = Field(default_factory=list)
    language: str = "ja"


class ParallelLifeExportRequest(BaseModel):
    """Request to export a Parallel Life reading as clean markdown."""

    result: ParallelLifeResult
    created_at: Optional[str] = None


class EditorialContext(BaseModel):
    """Optional answers from the Editorial Edition preparation step.
    Every field is optional; the user may skip any question."""

    life_before: Optional[str] = None
    changes_after: Optional[str] = None
    unseen_conditions: Optional[str] = None
    present_influence: Optional[str] = None
    meaning_of_unchosen_life: Optional[str] = None
    later_branches: Optional[str] = None
    current_life_context: Optional[str] = None
    social_connection: Optional[str] = None


class EditorialBranchStructure(BaseModel):
    """Internal multi-branch reading used to ground the Editorial Edition."""

    primary_branch: str
    realized_outcome: Optional[str] = None
    secondary_branches: list[str] = Field(default_factory=list)
    present_question: str = ""
    current_life_context: list[str] = Field(default_factory=list)
    explicit_facts: list[str] = Field(default_factory=list)
    inferred_themes: list[str] = Field(default_factory=list)


class NormalizedEditorialContext(BaseModel):
    """Deduplicated, classified facts for Editorial Edition writing.

    Raw user sentences must not enter public prose; generators interpret
    these normalized facts into authored editorial language.
    """

    explicit_facts: list[str] = Field(default_factory=list)
    present_life_facts: list[str] = Field(default_factory=list)
    emotional_observations: list[str] = Field(default_factory=list)
    current_roles: list[str] = Field(default_factory=list)
    current_conditions: list[str] = Field(default_factory=list)
    secondary_branches: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    # Compact signals for heuristic interpretation (not public prose).
    signals: list[str] = Field(default_factory=list)
    # All raw user strings retained only for reuse guards / whitelist.
    raw_source_corpus: list[str] = Field(default_factory=list)


class ParallelLifeEditorialClarifyRequest(BaseModel):
    """Request for optional Editorial Edition preparation questions."""

    source_text: str
    clarifications: ParallelLifeClarifications = Field(
        default_factory=ParallelLifeClarifications
    )
    language: str = "ja"
    answered_editorial_ids: list[str] = Field(default_factory=list)


class ParallelLifeEditorialRequest(BaseModel):
    """Request to generate the Editorial Edition (depth=editorial)."""

    source_text: str
    standard_result: Optional[ParallelLifeResult] = None
    clarifications: ParallelLifeClarifications = Field(
        default_factory=ParallelLifeClarifications
    )
    editorial_context: EditorialContext = Field(default_factory=EditorialContext)
    language: str = "ja"


class ParallelLifeEditorialResponse(BaseModel):
    """Editorial Edition response: multi-branch structure + full document."""

    branch_structure: EditorialBranchStructure
    result: ParallelLifeResult
