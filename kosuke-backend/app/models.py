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


class Fragment(BaseModel):
    """A minimal unit of thought."""

    id: str
    text: str
    source: str
    timestamp: str
    tags: list[str] = Field(default_factory=list)
    domain: Optional[str] = None  # domain tag for boundary-crossing flukes


class FragmentIngest(BaseModel):
    """Input model for ingesting text that will be chunked into fragments."""

    text: str
    source: str = "manual"
    tags: list[str] = Field(default_factory=list)
    domain: Optional[str] = None  # domain tag for boundary-crossing flukes
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


class ExportRequest(BaseModel):
    """Request model for exporting as markdown."""

    title: str = "Kosuke Protocol - Living Book"
    include_fragments: bool = True
    include_reflections: bool = True
    include_flukes: bool = False
