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


class ExportRequest(BaseModel):
    """Request model for exporting as markdown."""

    title: str = "Kosuke Protocol - Living Book"
    include_fragments: bool = True
    include_reflections: bool = True
    include_flukes: bool = False
