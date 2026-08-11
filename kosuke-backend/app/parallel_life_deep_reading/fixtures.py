"""Regression fixtures for Deep Reading Production Candidate v1.0.

Each fixture is an independent execution context — no shared state.
"""

from __future__ import annotations

from app.parallel_life_deep_reading.call1_schema import (
    AdditionalQuestions,
    Call1Response,
    EditorialOutline,
    LostStructure,
    ObservatoryLensSelection,
    ProtectedStructure,
    RebranchDesign,
    ResidueCandidates,
    SensitiveDomainAnalysis,
    SourceCoverage,
)
from app.parallel_life_deep_reading.models import (
    BranchClassification,
    BranchStructure,
    Call2Draft,
    CentralThesis,
    FactBoundaryType,
    GenerationStatus,
    GroundedFact,
    GroundedInput,
    InputSufficiency,
    ObservatoryLensCandidate,
    PrimaryBranch,
    RebranchDirection,
    ResidueCandidate,
    SecondaryBranch,
    UserConfirmationView,
)

FIXTURE_VERSION = "deep-reading-fixtures-v1.0"
Call1Result = Call1Response


def _fact(fid: str, content: str, source: str = "fixture") -> GroundedFact:
    return GroundedFact(
        id=fid,
        content=content,
        boundary_type=FactBoundaryType.explicit_fact,
        source_field=source,
        source_text=content,
        allowed_as_fact=True,
    )


def _feeling(fid: str, content: str) -> GroundedFact:
    return GroundedFact(
        id=fid,
        content=content,
        boundary_type=FactBoundaryType.user_feeling,
        allowed_as_fact=False,
        source_text=content,
    )


def _question(fid: str, content: str) -> GroundedFact:
    return GroundedFact(
        id=fid,
        content=content,
        boundary_type=FactBoundaryType.user_question,
        allowed_as_fact=False,
        source_text=content,
    )


CASE1_SOURCE = """45歳のとき、不妊治療を経て子どもを授かった。
実際に選んだのは、妻と息子と三人で暮らす人生だった。
選ばなかった道は、不妊治療を諦めることだった。
現在も妻と息子との三人家族で暮らし、自分の会社を経営している。
息子を可愛いと感じ、息子の友人が家に遊びに来ることを楽しいと感じている。
今も、二人目を持っていたらどうだったかと考えることがある。"""


def build_case1_call1(*, with_actual_secondary: bool = False) -> Call1Response:
    facts = [
        _fact("fact_001", "分岐が起きた年齢は45歳", CASE1_SOURCE),
        _fact("fact_002", "不妊治療を経て子どもを授かった", CASE1_SOURCE),
        _fact("fact_003", "実際に選んだ道は妻と息子と三人で暮らすこと", CASE1_SOURCE),
        _fact("fact_004", "選ばなかった道は不妊治療を諦めること", CASE1_SOURCE),
        _fact("fact_005", "現在は妻と息子との三人家族で暮らしている", CASE1_SOURCE),
        _fact("fact_006", "現在は自分の会社を経営している", CASE1_SOURCE),
    ]
    if with_actual_secondary:
        facts.append(
            _fact(
                "fact_007",
                "二人目を目指す治療を続けるか妻と話し合い、やめた",
                "clarification",
            )
        )

    questions = [_question("question_001", "二人目を持っていたらどうだったか")]
    feelings = [
        _feeling("feeling_001", "息子を可愛いと感じている"),
        _feeling("feeling_002", "息子の友人が家に遊びに来ることを楽しいと感じている"),
    ]

    secondary_branches: list[SecondaryBranch] = []
    counterfactuals: list[SecondaryBranch] = []
    if with_actual_secondary:
        secondary_branches.append(
            SecondaryBranch(
                id="sec_001",
                classification=BranchClassification.actual_secondary_branch,
                description="二人目を目指す治療を続けるか妻と話し合い、やめた",
                explicit_evidence_ids=["fact_007"],
            )
        )
    else:
        secondary_branches.append(
            SecondaryBranch(
                id="sec_bad",
                classification=BranchClassification.actual_secondary_branch,
                description="二人目がいたらどうだったか（問いのみ）",
                explicit_evidence_ids=["question_001"],
            )
        )
        counterfactuals.append(
            SecondaryBranch(
                id="cf_001",
                classification=BranchClassification.retrospective_counterfactual,
                description="二人目を持っていたらどうだったか",
                must_not_be_treated_as_historical_choice=True,
            )
        )

    evaluated = [
        ObservatoryLensCandidate(
            lens_id="body",
            explicit_evidence_ids=["fact_002"],
            residue_evidence_ids=[],
            new_meaning_added="",
            evidence_gate_passed=True,
        )
    ]

    return Call1Response(
        status=GenerationStatus.ready_for_user_confirmation,
        grounded_input=GroundedInput(
            facts=facts,
            feelings=feelings,
            questions=questions,
            current_context=[
                "妻と息子との三人家族で暮らしている",
                "自分の会社を経営している",
            ],
            confirmed_by_user=False,
        ),
        input_sufficiency=InputSufficiency(
            required_fields_complete=True,
            current_context_requirement_met=True,
        ),
        sensitive_domain_analysis=SensitiveDomainAnalysis(),
        branch_structure=BranchStructure(
            primary_branch=PrimaryBranch(
                period="45歳",
                triggering_event="不妊治療を経て子どもを授かった",
                realized_path="妻と息子と三人で暮らす",
                unrealized_paths=["不妊治療を諦める"],
                supporting_fact_ids=["fact_002", "fact_003", "fact_004"],
            ),
            secondary_branches=secondary_branches,
            retrospective_counterfactuals=counterfactuals,
            present_question_ids=["question_001"],
        ),
        central_thesis=CentralThesis(
            thesis_type="coexistence",
            statement="三人の暮らしへの肯定と、もう一人いたかもしれない家族への問いは同時に残りうる",
            pole_a="現在の三人家族への肯定",
            pole_b="二人目への問い",
            supported_by=["fact_005", "question_001"],
        ),
        lost_structure=LostStructure(),
        protected_structure=ProtectedStructure(),
        residue_candidates=ResidueCandidates(
            items=[
                ResidueCandidate(
                    residue_statement=(
                        "三人で暮らす選択のあとで、いまの家庭と経営の日常が続いており、"
                        "そのあいだに未接続の分岐が残っている"
                    ),
                    content=(
                        "三人で暮らす選択のあとで、いまの家庭と経営の日常が続いており、"
                        "そのあいだに未接続の分岐が残っている"
                    ),
                    past_anchor_ids=["fact_003"],
                    present_anchor_ids=["fact_005", "fact_006"],
                    support_ids=["fact_003", "fact_005", "fact_006"],
                    present_life_domain="family",
                    inference_distance="near",
                    advances_manuscript=True,
                )
            ]
        ),
        selected_observatory_lenses=ObservatoryLensSelection(
            evaluated=evaluated, selected=evaluated
        ),
        editorial_outline=EditorialOutline(),
        rebranch_design=RebranchDesign(
            directions=[
                RebranchDirection(
                    id="rb1",
                    source_meaning="息子に兄弟がいる家族へ託された、関係が家の内側に増える意味",
                    current_receiver="息子の友人が家に遊びに来る現在",
                    branch_specific_form="その場面が示す家庭らしさを一度だけ言葉にする",
                    support_ids=["fact_005", "feeling_002"],
                    genericity_score=0,
                    invented_scene_used=False,
                    publishable=True,
                    selected_for_manuscript=True,
                ),
                RebranchDirection(
                    id="rb_generic",
                    source_meaning="成長",
                    current_receiver="生活",
                    branch_specific_form="小さく始める",
                    support_ids=[],
                    genericity_score=3,
                    invented_scene_used=False,
                    publishable=True,
                    selected_for_manuscript=True,
                ),
            ]
        ),
        additional_questions=AdditionalQuestions(),
        user_confirmation_view=UserConfirmationView(
            branch_period="45歳",
            triggering_event="不妊治療を経て子どもを授かった",
            chosen_path="妻と息子と三人で暮らす",
            unchosen_path="不妊治療を諦める",
            central_thesis_preview="三人の暮らしへの肯定と二人目への問いは同時に残りうる",
        ),
        source_coverage=SourceCoverage(
            branch_period=True,
            triggering_event=True,
            chosen_path=True,
            unchosen_path=True,
            present_question=True,
            current_context=True,
        ),
    )


CASE1_BAD_DRAFT_BODY = """# 三人の暮らしに残る、もう一人の問い

45歳のとき、不妊治療を経て子どもを授かった。選んだのは、妻と息子との三人家族で暮らしていく道だった。

二人目を持っていたら、どうだっただろう。

夕方、息子の友人たちの声がリビングに響く。自分の会社の仕事を終え、家へ戻ったときなのか。

## 再分岐
まずは一つから、無理のない範囲で小さく始めよう。
"""


def build_case1_bad_draft() -> Call2Draft:
    return Call2Draft(
        body_markdown=CASE1_BAD_DRAFT_BODY,
        title_candidates=[
            "三人の暮らしに残る、もう一人の問い",
            "創作に残らなかった45歳",
            "かなった家族の隣の問い",
        ],
        subtitle_candidates=["かなった家族の隣に、選ばなかった可能性を置いてみる"],
        rebranch_candidates=[
            RebranchDirection(
                id="rb_generic",
                source_meaning="成長",
                current_receiver="",
                branch_specific_form="小さく始める",
                support_ids=[],
                genericity_score=3,
                invented_scene_used=False,
            )
        ],
        character_count=len(CASE1_BAD_DRAFT_BODY),
    )


CASE2_SOURCE = """19歳のとき、第一志望の早稲田大学第一文学部に合格した。
選ばなかった道は、別の大学へ進学することだった。
現在は複数の業界を経験したあと、文章やプロトコルをまとめている。
別の大学なら仕事や人間関係がどう変わったかと考えることがある。"""


def build_case2_call1() -> Call1Response:
    facts = [
        _fact("fact_101", "19歳で第一志望の早稲田大学第一文学部に合格した", CASE2_SOURCE),
        _fact("fact_102", "選ばなかった道は別の大学へ進学すること", CASE2_SOURCE),
        _fact("fact_103", "現在は複数業界を経験したあと文章やプロトコルをまとめている", CASE2_SOURCE),
    ]
    return Call1Response(
        status=GenerationStatus.ready_for_user_confirmation,
        grounded_input=GroundedInput(
            facts=facts,
            questions=[_question("question_101", "別の大学なら仕事や人間関係がどう変わったか")],
            current_context=["文章やプロトコルをまとめている"],
        ),
        input_sufficiency=InputSufficiency(
            required_fields_complete=True,
            current_context_requirement_met=True,
        ),
        branch_structure=BranchStructure(
            primary_branch=PrimaryBranch(
                period="19歳",
                triggering_event="第一志望の早稲田大学第一文学部に合格した",
                realized_path="早稲田大学第一文学部へ進学",
                unrealized_paths=["別の大学へ進学"],
                supporting_fact_ids=["fact_101", "fact_102"],
            ),
            secondary_branches=[
                SecondaryBranch(
                    id="sec_bad",
                    classification=BranchClassification.actual_secondary_branch,
                    description="不合格だった進路",
                    explicit_evidence_ids=[],
                )
            ],
            retrospective_counterfactuals=[
                SecondaryBranch(
                    id="cf_101",
                    classification=BranchClassification.retrospective_counterfactual,
                    description="別の大学なら仕事や人間関係がどう変わったか",
                    must_not_be_treated_as_historical_choice=True,
                )
            ],
        ),
        central_thesis=CentralThesis(
            statement="合格した進路の事実を保ったまま、別経路への問いは反実仮想として残る",
            supported_by=["fact_101", "question_101"],
        ),
        residue_candidates=ResidueCandidates(
            items=[
                ResidueCandidate(
                    residue_statement=(
                        "第一志望への進学という分岐のあとで、文章やプロトコルをまとめる現在が続いており、"
                        "そのあいだに経路の未接続が残っている"
                    ),
                    content=(
                        "第一志望への進学という分岐のあとで、文章やプロトコルをまとめる現在が続いており、"
                        "そのあいだに経路の未接続が残っている"
                    ),
                    past_anchor_ids=["fact_101"],
                    present_anchor_ids=["fact_103"],
                    support_ids=["fact_101", "fact_103"],
                    inference_distance="near",
                    advances_manuscript=True,
                )
            ]
        ),
        selected_observatory_lenses=ObservatoryLensSelection(
            evaluated=[
                ObservatoryLensCandidate(
                    lens_id="education-employment",
                    explicit_evidence_ids=["fact_101"],
                    residue_evidence_ids=[],
                    new_meaning_added="",
                    evidence_gate_passed=True,
                )
            ],
            selected=[],
        ),
        rebranch_design=RebranchDesign(
            directions=[
                RebranchDirection(
                    id="rb2",
                    source_meaning="別の大学に託された、異なる人・知識・仕事との接続順序",
                    current_receiver="現在制作している文章またはプロトコル",
                    branch_specific_form="複数業界のうち一度の業界移動を題材にする",
                    support_ids=["fact_103"],
                    genericity_score=0,
                )
            ]
        ),
        user_confirmation_view=UserConfirmationView(
            branch_period="19歳",
            triggering_event="第一志望の早稲田大学第一文学部に合格した",
            chosen_path="早稲田大学第一文学部へ進学",
            unchosen_path="別の大学へ進学",
        ),
        source_coverage=SourceCoverage(
            branch_period=True,
            triggering_event=True,
            chosen_path=True,
            unchosen_path=True,
            present_question=True,
            current_context=True,
        ),
    )


CASE3_SOURCE = """会社員として複数業界で働いてきた。
選ばなかった道は、創作を中心にした人生だった。
現在は企業での経験を持ちつつ、観測サイトや文章、プロトコルを制作している。
創作中心なら今とは違う人生だったかと考えることがある。"""


def build_case3_call1() -> Call1Response:
    facts = [
        _fact("fact_201", "会社員として複数業界で働いてきた", CASE3_SOURCE),
        _fact("fact_202", "選ばなかった道は創作を中心にした人生", CASE3_SOURCE),
        _fact("fact_203", "現在は観測サイトや文章、プロトコルを制作している", CASE3_SOURCE),
    ]
    return Call1Response(
        status=GenerationStatus.ready_for_user_confirmation,
        grounded_input=GroundedInput(
            facts=facts,
            questions=[_question("question_201", "創作中心なら今とは違う人生だったか")],
            current_context=["観測サイトや文章、プロトコルを制作している"],
        ),
        input_sufficiency=InputSufficiency(
            required_fields_complete=True,
            current_context_requirement_met=True,
        ),
        branch_structure=BranchStructure(
            primary_branch=PrimaryBranch(
                period="社会人期",
                triggering_event="会社員として複数業界で働く道を進んだ",
                realized_path="企業キャリア",
                unrealized_paths=["創作中心の人生"],
                supporting_fact_ids=["fact_201", "fact_202"],
            ),
            secondary_branches=[],
            retrospective_counterfactuals=[
                SecondaryBranch(
                    id="cf_201",
                    classification=BranchClassification.retrospective_counterfactual,
                    description="創作中心なら今とは違う人生だったか",
                    must_not_be_treated_as_historical_choice=True,
                )
            ],
        ),
        central_thesis=CentralThesis(
            statement="企業キャリアを劣位とみなさず、創作中心の人生も理想化せず、現在の制作へ接続できる",
            supported_by=["fact_201", "fact_203"],
        ),
        residue_candidates=ResidueCandidates(
            items=[
                ResidueCandidate(
                    residue_statement=(
                        "会社員としての経験という分岐のあとで、観測サイトや文章の制作という現在が続いており、"
                        "そのあいだに創作側へ託されていた接続が残っている"
                    ),
                    content=(
                        "会社員としての経験という分岐のあとで、観測サイトや文章の制作という現在が続いており、"
                        "そのあいだに創作側へ託されていた接続が残っている"
                    ),
                    past_anchor_ids=["fact_201"],
                    present_anchor_ids=["fact_203"],
                    support_ids=["fact_201", "fact_203"],
                    inference_distance="near",
                    advances_manuscript=True,
                )
            ]
        ),
        selected_observatory_lenses=ObservatoryLensSelection(
            evaluated=[
                ObservatoryLensCandidate(
                    lens_id="work",
                    explicit_evidence_ids=["fact_201"],
                    residue_evidence_ids=[],
                    new_meaning_added="職業名があるだけ",
                    evidence_gate_passed=True,
                )
            ],
            selected=[],
        ),
        rebranch_design=RebranchDesign(
            directions=[
                RebranchDirection(
                    id="rb3",
                    source_meaning="創作中心の人生に託されていた、経験を作品の形にする意味",
                    current_receiver="現在の観測サイト・文章・プロトコル",
                    branch_specific_form="複数業界の一経験を、選んだ媒体固有の形式で一件残す",
                    support_ids=["fact_203"],
                    genericity_score=0,
                ),
                RebranchDirection(
                    id="rb3_bad",
                    source_meaning="創作",
                    current_receiver="生活",
                    branch_specific_form="創作の時間を確保する",
                    support_ids=["fact_203"],
                    genericity_score=2,
                    publishable=True,
                ),
            ]
        ),
        user_confirmation_view=UserConfirmationView(
            branch_period="社会人期",
            triggering_event="会社員として複数業界で働いてきた",
            chosen_path="企業キャリア",
            unchosen_path="創作中心の人生",
        ),
        source_coverage=SourceCoverage(
            branch_period=True,
            triggering_event=True,
            chosen_path=True,
            unchosen_path=True,
            present_question=True,
            current_context=True,
        ),
    )


REGRESSION_FIXTURES = {
    "case1_family_question_only": {
        "source": CASE1_SOURCE,
        "build_call1": lambda: build_case1_call1(with_actual_secondary=False),
        "expectations": {
            "actual_secondary_count": 0,
            "counterfactual_min": 1,
            "selected_lenses_max": 0,
            "no_creativity_takeover": True,
        },
    },
    "case1_family_with_decision": {
        "source": CASE1_SOURCE,
        "build_call1": lambda: build_case1_call1(with_actual_secondary=True),
        "expectations": {
            "actual_secondary_count": 1,
            "selected_lenses_max": 0,
        },
    },
    "case2_university": {
        "source": CASE2_SOURCE,
        "build_call1": build_case2_call1,
        "expectations": {
            "actual_secondary_count": 0,
            "must_keep_admission": True,
            "selected_lenses_max": 0,
        },
    },
    "case3_creative_corporate": {
        "source": CASE3_SOURCE,
        "build_call1": build_case3_call1,
        "expectations": {
            "actual_secondary_count": 0,
            "selected_lenses_max": 0,
            "generic_rebranch_rejected": True,
        },
    },
}
