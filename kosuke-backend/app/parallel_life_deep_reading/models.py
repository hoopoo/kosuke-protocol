"""Pydantic models for Deep Reading Production Candidate v1.0."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class FactBoundaryType(str, Enum):
    explicit_fact = "explicit_fact"
    user_feeling = "user_feeling"
    user_question = "user_question"
    user_hypothesis = "user_hypothesis"
    unknown = "unknown"
    model_inference = "model_inference"


class BranchClassification(str, Enum):
    actual_secondary_branch = "actual_secondary_branch"
    retrospective_counterfactual = "retrospective_counterfactual"


class GenerationStatus(str, Enum):
    ready_for_user_confirmation = "ready_for_user_confirmation"
    needs_additional_input = "needs_additional_input"
    structural_ambiguity = "structural_ambiguity"
    insufficient_current_context = "insufficient_current_context"
    sensitive_domain_clarification_required = "sensitive_domain_clarification_required"
    # v1.1.9: terminal clarification exit (HTTP 200, no loop)
    insufficient_for_deep_reading = "insufficient_for_deep_reading"
    schema_validation_failed = "schema_validation_failed"
    ready_for_draft = "ready_for_draft"
    draft_generated = "draft_generated"
    validation_failed = "validation_failed"
    editorial_failure = "editorial_failure"
    complete = "complete"


class ValidationCategory(str, Enum):
    supported = "supported"
    qualified_inference = "qualified_inference"
    unsupported = "unsupported"
    contradiction = "contradiction"


class ActualSecondaryBranchEvidenceType(str, Enum):
    actually_hesitated = "actually_hesitated"
    actually_considered = "actually_considered"
    continue_stop_decision = "continue_stop_decision"
    action_started_or_ended = "action_started_or_ended"


GenericityScore = Literal[0, 1, 2, 3]


class GroundedFact(BaseModel):
    id: str = ""
    content: str = ""
    boundary_type: FactBoundaryType = FactBoundaryType.explicit_fact
    source_field: str = ""
    source_text: str = ""
    confidence: float = 1.0
    allowed_as_fact: bool = True
    inference_distance: str = "none"
    supported_by: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class GroundedInput(BaseModel):
    facts: list[GroundedFact] = Field(default_factory=list)
    feelings: list[GroundedFact] = Field(default_factory=list)
    questions: list[GroundedFact] = Field(default_factory=list)
    hypotheses: list[GroundedFact] = Field(default_factory=list)
    unknowns: list[GroundedFact] = Field(default_factory=list)
    model_inferences: list[GroundedFact] = Field(default_factory=list)
    current_context: list[str] = Field(default_factory=list)
    sensitive_domains: list[str] = Field(default_factory=list)
    confirmed_by_user: bool = False
    requested_corrections: list[str] = Field(default_factory=list)


class InputSufficiency(BaseModel):
    required_fields_complete: bool = False
    current_context_requirement_met: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    additional_questions: list[str] = Field(default_factory=list)


class PrimaryBranch(BaseModel):
    period: str = ""
    triggering_event: str = ""
    available_paths: list[str] = Field(default_factory=list)
    realized_path: str = ""
    unrealized_paths: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    supporting_fact_ids: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)


class SecondaryBranch(BaseModel):
    id: str = ""
    classification: BranchClassification = BranchClassification.retrospective_counterfactual
    parent_branch_id: str = "primary"
    description: str = ""
    available_paths: list[str] = Field(default_factory=list)
    realized_path: str = ""
    unrealized_paths: list[str] = Field(default_factory=list)
    explicit_evidence_ids: list[str] = Field(default_factory=list)
    evidence_type: Optional[ActualSecondaryBranchEvidenceType] = None
    ambiguity_status: str = ""
    present_relevance: str = ""
    must_not_be_treated_as_historical_choice: bool = False


class BranchStructure(BaseModel):
    primary_branch: PrimaryBranch = Field(default_factory=PrimaryBranch)
    realized_outcomes: list[str] = Field(default_factory=list)
    secondary_branches: list[SecondaryBranch] = Field(default_factory=list)
    retrospective_counterfactuals: list[SecondaryBranch] = Field(default_factory=list)
    present_question_ids: list[str] = Field(default_factory=list)


class CentralThesis(BaseModel):
    thesis_type: str = ""
    statement: str = ""
    pole_a: str = ""
    pole_b: str = ""
    supported_by: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    validation_status: str = "pending"


class LostItem(BaseModel):
    content: str = ""
    loss_type: str = ""
    support_ids: list[str] = Field(default_factory=list)
    certainty: str = "qualified"
    allowed_wording_strength: str = "qualified"


class ConfirmedContinuity(BaseModel):
    content: str = ""
    support_ids: list[str] = Field(default_factory=list)
    causality_status: str = "observed"
    allowed_statement_strength: str = "supported"


class PossibleProtection(BaseModel):
    content: str = ""
    support_ids: list[str] = Field(default_factory=list)
    inference_distance: str = "near"
    causality_confirmed: bool = False
    required_qualification: str = ""
    exclusion_risk: str = ""


class ResidueCandidate(BaseModel):
    """Structural connection from past branch anchors to present-life anchors.

    user_question alone is never Residue.
    """

    residue_statement: str = ""
    content: str = ""  # legacy alias; prefer residue_statement
    past_anchor_ids: list[str] = Field(default_factory=list)
    present_anchor_ids: list[str] = Field(default_factory=list)
    support_ids: list[str] = Field(default_factory=list)
    inference_distance: str = "near"  # near | medium | far
    present_life_domain: str = ""
    overreach_risk: str = ""
    advances_manuscript: bool = True

    def statement(self) -> str:
        return (self.residue_statement or self.content or "").strip()


class ObservatoryLensCandidate(BaseModel):
    lens_id: str = ""
    explicit_evidence_ids: list[str] = Field(default_factory=list)
    residue_evidence_ids: list[str] = Field(default_factory=list)
    new_meaning_added: str = ""
    evidence_gate_passed: bool = False
    rejection_reason: str = ""
    confidence: float = 0.0


class EditorialSectionPlan(BaseModel):
    internal_id: str = ""
    public_heading: str = ""
    required: bool = True
    new_meaning: str = ""
    allowed_boundary_ids: list[str] = Field(default_factory=list)
    forbidden_inferences: list[str] = Field(default_factory=list)
    previous_section_difference: str = ""
    next_section_transition: str = ""
    reserved_fact_ids: list[str] = Field(default_factory=list)
    prohibited_repeat_ids: list[str] = Field(default_factory=list)
    relative_weight: float = 1.0


class RebranchDirection(BaseModel):
    id: str = ""
    source_meaning: str = ""
    current_receiver: str = ""
    branch_specific_form: str = ""
    support_ids: list[str] = Field(default_factory=list)
    genericity_score: GenericityScore = 2
    invented_scene_used: bool = False
    risks: list[str] = Field(default_factory=list)
    publishable: bool = False
    selected_for_manuscript: bool = False


class UserConfirmationView(BaseModel):
    """Non-technical confirmation payload for the frontend."""

    branch_period: str = ""
    triggering_event: str = ""
    chosen_path: str = ""
    unchosen_path: str = ""
    actual_secondary_branches: list[str] = Field(default_factory=list)
    retrospective_counterfactuals: list[str] = Field(default_factory=list)
    present_questions: list[str] = Field(default_factory=list)
    current_context: list[str] = Field(default_factory=list)
    feelings: list[str] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    central_thesis_preview: str = ""
    observatory_lens_candidates: list[str] = Field(default_factory=list)
    items_to_confirm: list[str] = Field(default_factory=list)


class Call1Validation(BaseModel):
    actual_secondary_rejected: list[str] = Field(default_factory=list)
    lenses_rejected: list[str] = Field(default_factory=list)
    questions_not_converted_to_facts: bool = True
    hypotheses_not_converted_to_facts: bool = True
    notes: list[str] = Field(default_factory=list)
    source_coverage_missing: list[str] = Field(default_factory=list)
    # v1.0.1 release-blocker diagnostics (server-side)
    material_contradictions: list[str] = Field(default_factory=list)
    material_contradiction_count: int = 0
    branch_concreteness_ok: bool = True
    thesis_deferred_due_to_contradiction: bool = False
    sensitive_thesis_rejected: bool = False


CALL_1_SCHEMA_VERSION = "parallel-life-call-1-schema-v1.0.2"
CALL_1_PROMPT_VERSION = "parallel-life-call-1-v1.0.3"


class SensitiveDomainAnalysis(BaseModel):
    domains: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    clarification_required: bool = False


class LostStructure(BaseModel):
    items: list[LostItem] = Field(default_factory=list)


class ProtectedStructure(BaseModel):
    items: list[ConfirmedContinuity] = Field(default_factory=list)


class ResidueCandidates(BaseModel):
    items: list[ResidueCandidate] = Field(default_factory=list)


class ObservatoryLensSelection(BaseModel):
    evaluated: list[ObservatoryLensCandidate] = Field(default_factory=list)
    selected: list[ObservatoryLensCandidate] = Field(default_factory=list)


class EditorialOutline(BaseModel):
    sections: list[EditorialSectionPlan] = Field(default_factory=list)


class RepetitionMapEntry(BaseModel):
    key: str = ""
    ids: list[str] = Field(default_factory=list)


class RepetitionPreventionMap(BaseModel):
    entries: list[RepetitionMapEntry] = Field(default_factory=list)

    def as_dict(self) -> dict[str, list[str]]:
        return {e.key: list(e.ids) for e in self.entries if e.key}


class RebranchDesign(BaseModel):
    directions: list[RebranchDirection] = Field(default_factory=list)


class AdditionalQuestions(BaseModel):
    required: bool = False
    questions: list[str] = Field(default_factory=list)


class SourceCoverage(BaseModel):
    branch_period: bool = False
    triggering_event: bool = False
    chosen_path: bool = False
    unchosen_path: bool = False
    present_question: bool = False
    current_context: bool = False

    def all_required_present(self) -> bool:
        return all(
            [
                self.branch_period,
                self.triggering_event,
                self.chosen_path,
                self.unchosen_path,
                self.present_question,
                self.current_context,
            ]
        )

    def missing(self) -> list[str]:
        return [
            name
            for name in (
                "branch_period",
                "triggering_event",
                "chosen_path",
                "unchosen_path",
                "present_question",
                "current_context",
            )
            if not getattr(self, name)
        ]


class Call1ParseDiagnostics(BaseModel):
    validation_errors: list[str] = Field(default_factory=list)
    offending_paths: list[str] = Field(default_factory=list)
    repair_attempted: bool = False
    repair_succeeded: bool = False
    normalization_applied: list[str] = Field(default_factory=list)
    raw_response_saved_in_dev_only: bool = False


class ContextRelevanceClassification(BaseModel):
    id: str = ""
    relevance: str = "supporting"  # essential | supporting | irrelevant_for_this_branch
    reason: str = ""


class RelevantContextSelection(BaseModel):
    """v1.1.1-exp: which approved pack items drive manuscript logic."""

    selected_ids: list[str] = Field(default_factory=list)
    classifications: list[ContextRelevanceClassification] = Field(default_factory=list)
    manuscript_logic_ids: list[str] = Field(default_factory=list)
    withheld_ids: list[str] = Field(default_factory=list)


class MeaningCompression(BaseModel):
    """v1.1.1+ structural compression before central thesis.

    v1.1.2-exp adds personal/social/present/unresolved fields fed by CrossLensRelations.
    """

    past_structure: str = ""
    alternative_structure: str = ""
    present_structure: str = ""
    tension: str = ""
    continuity: str = ""
    transformation: str = ""
    central_question: str = ""
    # v1.1.2-exp Observatory-Core (optional; empty in Strict / v1.1.1)
    personal_tension: str = ""
    social_institutional_parallel: str = ""
    present_life_connection: str = ""
    unresolved_question: str = ""
    cross_lens_relation_ids: list[str] = Field(default_factory=list)
    support_ids: list[str] = Field(default_factory=list)
    validation_status: str = "pending"


class Call1LLMPayload(BaseModel):
    """Exact object the model must return (no server-only fields)."""

    status: GenerationStatus = GenerationStatus.ready_for_user_confirmation
    grounded_input: GroundedInput = Field(default_factory=GroundedInput)
    input_sufficiency: InputSufficiency = Field(default_factory=InputSufficiency)
    sensitive_domain_analysis: SensitiveDomainAnalysis = Field(
        default_factory=SensitiveDomainAnalysis
    )
    branch_structure: BranchStructure = Field(default_factory=BranchStructure)
    # v1.1.1-exp additive (empty defaults keep Strict / older models schema-compatible)
    relevant_context_selection: RelevantContextSelection = Field(
        default_factory=RelevantContextSelection
    )
    meaning_compression: MeaningCompression = Field(default_factory=MeaningCompression)
    central_thesis: CentralThesis = Field(default_factory=CentralThesis)
    lost_structure: LostStructure = Field(default_factory=LostStructure)
    protected_structure: ProtectedStructure = Field(default_factory=ProtectedStructure)
    residue_candidates: ResidueCandidates = Field(default_factory=ResidueCandidates)
    selected_observatory_lenses: ObservatoryLensSelection = Field(
        default_factory=ObservatoryLensSelection
    )
    editorial_outline: EditorialOutline = Field(default_factory=EditorialOutline)
    repetition_prevention_map: RepetitionPreventionMap = Field(
        default_factory=RepetitionPreventionMap
    )
    rebranch_design: RebranchDesign = Field(default_factory=RebranchDesign)
    additional_questions: AdditionalQuestions = Field(default_factory=AdditionalQuestions)
    user_confirmation_view: UserConfirmationView = Field(default_factory=UserConfirmationView)
    validation: Call1Validation = Field(default_factory=Call1Validation)
    source_coverage: SourceCoverage = Field(default_factory=SourceCoverage)


class Call1Result(Call1LLMPayload):
    """Canonical Call 1 contract — LLM payload + server metadata."""

    prompt_version: str = CALL_1_PROMPT_VERSION
    schema_version: str = CALL_1_SCHEMA_VERSION
    parse_diagnostics: Optional[Call1ParseDiagnostics] = None
    # v1.1-exp only: which pack IDs were used as anchors / lens evidence / rebranch supports
    context_pack_usage: Optional[dict[str, Any]] = None
    # v1.1.1-exp diagnostics (server-filled; not required from LLM)
    resume_density_report: Optional[dict[str, Any]] = None
    selection_compression_diagnostics: Optional[dict[str, Any]] = None
    # v1.1.2-exp Observatory-Core (server-filled; not required from LLM schema)
    candidate_lens_selection: Optional[dict[str, Any]] = None
    retrieved_observatory_evidence: Optional[list[dict[str, Any]]] = None
    cross_lens_relations: Optional[list[dict[str, Any]]] = None
    observatory_core_diagnostics: Optional[dict[str, Any]] = None
    # v1.1.3-exp Section Contracts (server-filled)
    section_contracts: Optional[dict[str, Any]] = None
    call2_writing_pack_diagnostics: Optional[dict[str, Any]] = None
    # v1.1.8-exp BranchSemantics (server-filled; domain-neutral pre-thesis layer)
    branch_semantics: Optional[dict[str, Any]] = None


Call1Response = Call1Result


class DraftSectionMeta(BaseModel):
    internal_id: str = ""
    public_heading: str = ""
    included: bool = True
    char_count: int = 0


class ParagraphSupport(BaseModel):
    paragraph_id: str = ""
    support_ids: list[str] = Field(default_factory=list)
    contains_inference: bool = False
    text_preview: str = ""


class Call2Draft(BaseModel):
    body_markdown: str = ""
    title_candidates: list[str] = Field(default_factory=list)
    subtitle_candidates: list[str] = Field(default_factory=list)
    sections: list[DraftSectionMeta] = Field(default_factory=list)
    rebranch_candidates: list[RebranchDirection] = Field(default_factory=list)
    rebranch_omitted_reason: Optional[str] = None
    observatory_omitted: bool = False
    paragraph_support: list[ParagraphSupport] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    prompt_version: str = "parallel-life-call-2-v1.0.3"
    character_count: int = 0


class UnsupportedScene(BaseModel):
    excerpt: str
    scene_type: str
    missing_support: str
    category: ValidationCategory = ValidationCategory.unsupported


class UnsupportedPersonalDetail(BaseModel):
    excerpt: str
    detail_type: str
    missing_support: str
    category: ValidationCategory = ValidationCategory.unsupported


class UnsupportedCausality(BaseModel):
    excerpt: str
    causality_strength: int = 3  # 0–3
    missing_support: str = ""
    category: ValidationCategory = ValidationCategory.unsupported


class UnsupportedAffect(BaseModel):
    excerpt: str
    affect_type: str
    missing_support: str = ""
    category: ValidationCategory = ValidationCategory.unsupported


class UnsupportedRoleBehavior(BaseModel):
    excerpt: str
    role_type: str
    missing_support: str = ""
    category: ValidationCategory = ValidationCategory.unsupported


class UnsupportedCausalFrame(BaseModel):
    excerpt: str
    frame_type: str = "causal_presupposition"
    missing_support: str = ""
    category: ValidationCategory = ValidationCategory.unsupported


class SchemaLeakageProse(BaseModel):
    excerpt: str
    leakage_type: str = "schema_verbalization"
    missing_support: str = ""
    category: ValidationCategory = ValidationCategory.unsupported


class UnrealizedPathModalityViolation(BaseModel):
    excerpt: str
    unrealized_path: str = ""
    modality_type: str = "realized_event_modality"
    missing_support: str = "path_is_unrealized_or_counterfactual"
    category: ValidationCategory = ValidationCategory.unsupported


class GenericAdviceFinding(BaseModel):
    excerpt: str
    case_specific_object_present: bool = False
    reason_present: bool = False
    current_context_present: bool = False
    category: ValidationCategory = ValidationCategory.unsupported


class TitleValidation(BaseModel):
    selected_title: str = ""
    selected_subtitle: str = ""
    title_supported_by_fact_ids: list[str] = Field(default_factory=list)
    title_supported_by_central_thesis: bool = False
    title_introduces_new_unverified_theme: bool = False
    title_factual_consistency: bool = False
    title_overdramatizes_unchosen_life: bool = False
    title_matches_final_closing: bool = False
    title_causal_frame_violation: bool = False
    passed: bool = False
    notes: list[str] = Field(default_factory=list)


class Call3Validation(BaseModel):
    unsupported_scenes: list[UnsupportedScene] = Field(default_factory=list)
    unsupported_personal_details: list[UnsupportedPersonalDetail] = Field(
        default_factory=list
    )
    unsupported_causality: list[UnsupportedCausality] = Field(default_factory=list)
    unsupported_affect: list[UnsupportedAffect] = Field(default_factory=list)
    unsupported_role_behavior: list[UnsupportedRoleBehavior] = Field(
        default_factory=list
    )
    unsupported_causal_frame: list[UnsupportedCausalFrame] = Field(default_factory=list)
    schema_leakage_prose: list[SchemaLeakageProse] = Field(default_factory=list)
    unrealized_path_modality_violations: list[UnrealizedPathModalityViolation] = Field(
        default_factory=list
    )
    generic_advice_findings: list[GenericAdviceFinding] = Field(default_factory=list)
    rebranch_validations: list[RebranchDirection] = Field(default_factory=list)
    title_validation: TitleValidation = Field(default_factory=TitleValidation)
    contradictions: list[str] = Field(default_factory=list)
    questions_converted_to_facts: list[str] = Field(default_factory=list)
    hypotheses_converted_to_facts: list[str] = Field(default_factory=list)
    protections_stated_as_facts: list[str] = Field(default_factory=list)
    unknowns_filled_by_model: list[str] = Field(default_factory=list)
    sentence_fragments: list[str] = Field(default_factory=list)
    copied_long_input_segments: list[str] = Field(default_factory=list)
    unsupported_paragraphs: list[str] = Field(default_factory=list)
    unsupported_causality_count: int = 0
    unsupported_affect_count: int = 0
    unsupported_role_behavior_count: int = 0
    unsupported_causal_frame_count: int = 0
    schema_leakage_prose_count: int = 0
    unrealized_path_modality_violation_count: int = 0
    unsupported_personal_detail_count: int = 0
    unsupported_scene_count: int = 0
    manual_fidelity_gap_possible: bool = False
    central_thesis_maintained: bool = True
    residue_centrality: bool = True
    observatory_takeover: bool = False
    closing_returns_to_present: bool = True
    required_section_realization_ok: bool = True
    required_section_realization_details: dict[str, Any] = Field(default_factory=dict)
    resume_density_report: Optional[dict[str, Any]] = None
    publishable: bool = False
    blocking_reasons: list[str] = Field(default_factory=list)


class Call3Result(BaseModel):
    status: GenerationStatus = GenerationStatus.complete
    final_title: str = ""
    final_subtitle: str = ""
    body_markdown: str = ""
    validation: Call3Validation = Field(default_factory=Call3Validation)
    prompt_version: str = "parallel-life-call-3-v1.0.3"
    character_count: int = 0


class DeepReadingSession(BaseModel):
    """Server-side session — request-scoped isolation, no cross-case leakage."""

    session_id: str
    raw_user_input: str = ""
    language: str = "ja"
    clarifications: dict[str, Any] = Field(default_factory=dict)
    editorial_context: dict[str, Any] = Field(default_factory=dict)
    call1: Optional[Call1Result] = None
    user_corrections: list[str] = Field(default_factory=list)
    confirmation_timestamp: Optional[str] = None
    call2: Optional[Call2Draft] = None
    call3: Optional[Call3Result] = None
    final_manuscript: Optional[str] = None
    generation_attempt_count: int = 0
    draft_attempt_count: int = 0
    edit_attempt_count: int = 0
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    model_metadata: dict[str, Any] = Field(default_factory=dict)
    status: GenerationStatus = GenerationStatus.ready_for_user_confirmation
    legacy: bool = False
    schema_version: str = "parallel-life-runtime-v1.0.6"
    created_at: str = ""
    updated_at: str = ""
    # Cloudflare / multi-instance persistence (additive; default-safe for memory store)
    session_revision: int = 0
    expires_at: str = ""
    # Map idempotency_key -> stage result marker (e.g. "draft:complete")
    idempotency_keys: dict[str, str] = Field(default_factory=dict)
    # v1.1-exp Context Pack (additive; ignored by Strict / prod default)
    deep_reading_mode: str = "strict"
    context_pack: Optional[dict[str, Any]] = None


# --- API request / response models ---


class DeepReadingGroundRequest(BaseModel):
    source_text: str
    clarifications: dict[str, Any] = Field(default_factory=dict)
    editorial_context: dict[str, Any] = Field(default_factory=dict)
    language: str = "ja"
    answers_to_additional_questions: dict[str, str] = Field(default_factory=dict)
    # v1.1-exp additive fields (default keeps v1.0.2 Strict behavior)
    deep_reading_mode: Literal["strict", "contextual"] = "strict"
    context_pack: Optional[dict[str, Any]] = None


class DeepReadingConfirmRequest(BaseModel):
    session_id: str
    action: Literal["approve", "edit", "answer", "abort"] = "approve"
    corrections: dict[str, Any] = Field(default_factory=dict)
    answers_to_additional_questions: dict[str, str] = Field(default_factory=dict)
    confirmation_view_overrides: Optional[UserConfirmationView] = None


class DeepReadingDraftRequest(BaseModel):
    session_id: str
    idempotency_key: Optional[str] = None


class DeepReadingEditValidateRequest(BaseModel):
    session_id: str
    idempotency_key: Optional[str] = None


class DeepReadingRegenerateRequest(BaseModel):
    session_id: str
    from_stage: Literal["ground", "draft", "edit-validate"] = "draft"


class DeepReadingExportRequest(BaseModel):
    session_id: str
    include_diagnostics: bool = False


class DeepReadingSessionResponse(BaseModel):
    session: DeepReadingSession
    progress_label: str = ""
    diagnostics: Optional[dict[str, Any]] = None
    # v1.1.8 clarification UX — normal intermediate state (HTTP 200)
    status: Optional[str] = None
    questions: list[str] = Field(default_factory=list)
    clarification_required: bool = False
    # v1.1.9 clarification exit / terminal reason (user-facing, optional)
    clarification_exit_reason: Optional[str] = None
