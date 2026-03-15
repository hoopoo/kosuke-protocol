"""Pydantic models for Kosuke Protocol."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FragmentCreate(BaseModel):
    """Input model for creating a fragment."""

    text: str
    source: str = "manual"
    tags: list[str] = Field(default_factory=list)


class Fragment(BaseModel):
    """A minimal unit of thought."""

    id: str
    text: str
    source: str
    timestamp: str
    tags: list[str] = Field(default_factory=list)


class FragmentIngest(BaseModel):
    """Input model for ingesting text that will be chunked into fragments."""

    text: str
    source: str = "manual"
    tags: list[str] = Field(default_factory=list)
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


class FlukeResult(BaseModel):
    """Output model for a generated fluke."""

    fragment_a: Fragment
    fragment_b: Fragment
    distance: float
    core_resonance: float
    tension_score: float
    context_fit: float
    fluke_score: float
    tension: str
    reflection_prompt: str


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


class ExportRequest(BaseModel):
    """Request model for exporting as markdown."""

    title: str = "Kosuke Protocol - Living Book"
    include_fragments: bool = True
    include_reflections: bool = True
    include_flukes: bool = False
