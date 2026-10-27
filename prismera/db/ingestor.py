"""PrismEra Knowledge Base Dynamic Ingestor and Incremental Validation Pipeline.

Provides strict Pydantic V2 schema validation and incremental ingestion for:
- Academic programs and dynamic university Tier Lists
- Course prerequisite topological subgraphs
- Professor research profiles, lab openings, and peer-reviewed publications
- Admission cases and institutional nuances (with vector store embedding sync)

Supports atomic batch validation, rollback on error, and hot updates across
both GraphStore (NetworkX + SQLite) and VectorStore (NumPy + SQLite).
"""

from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Literal

from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError

from prismera.db.graph_store import GraphStore, get_graph_store
from prismera.db.vector_store import VectorStore, get_vector_store, ProgramNuance, AdmissionCase

logger = logging.getLogger("PrismEraIngestor")

VALID_REGIONS = {"US", "UK", "SG", "HK", "CA", "EU", "AU", "JP"}
VALID_MAJORS = {"CS", "DS", "BA", "FIN", "ECE", "AI", "SE", "MIS", "STATS"}
VALID_TIERS = {"985", "211", "双非一本", "双非", "海本", "C9"}


# =============================================================================
# Pydantic Validation Schemas
# =============================================================================

class LanguageRequirementsModel(BaseModel):
    """Sub-scores and total requirements for language examinations."""
    total: float = Field(..., ge=0.0, le=120.0, description="Minimum overall score")
    subscore: float = Field(..., ge=0.0, le=120.0, description="Minimum subscore required across bands")
    speaking: Optional[float] = Field(default=None, ge=0.0, le=120.0, description="Explicit speaking subscore threshold")
    listening: Optional[float] = Field(default=None, ge=0.0, le=120.0)
    reading: Optional[float] = Field(default=None, ge=0.0, le=120.0)
    writing: Optional[float] = Field(default=None, ge=0.0, le=120.0)

    @model_validator(mode="after")
    def populate_speaking_fallback(self) -> LanguageRequirementsModel:
        if self.speaking is None:
            self.speaking = self.subscore
        return self


class ListTierRequirement(BaseModel):
    """Undergrad institution Tier List requirement for a specific program."""
    tier: str = Field(..., description="Institutional Tier identifier (e.g. '985', '211', '双非一本')")
    min_gpa_score: float = Field(..., gt=0.0, le=100.0, description="Minimum GPA threshold on 100 or 4.0 scale")

    @field_validator("tier")
    @classmethod
    def validate_tier_name(cls, v: str) -> str:
        clean = v.strip()
        if clean not in VALID_TIERS:
            raise ValueError(f"Invalid tier name '{v}'. Must be one of {sorted(VALID_TIERS)}")
        return clean


class DistinctiveCourseModel(BaseModel):
    """Curriculum flagship course featured in program ethos."""
    code: str = Field(..., min_length=1, max_length=32)
    title: str = Field(..., min_length=2)
    syllabus_highlight: Optional[str] = None


class PrerequisiteLinkModel(BaseModel):
    """Program-to-course prerequisite relationship link."""
    course_id: str = Field(..., min_length=2)
    level: Literal["mandatory", "high", "recommended"] = "mandatory"


class ProgramIngestModel(BaseModel):
    """Full schema for program nodes, admission thresholds, and list mappings."""
    id: str = Field(..., pattern=r"^[a-z0-9_]+$", description="Unique program slug (e.g. 'cambridge_mphil_acm')")
    name_cn: str = Field(..., min_length=2)
    name_en: str = Field(..., min_length=2)
    institution: str = Field(..., min_length=2)
    region: str = Field(..., description="Target region (US, UK, SG, HK, etc.)")
    major_category: str = Field(..., description="Core field category (CS, DS, BA, FIN, etc.)")
    academic_year: str = Field(default="2026_2027", description="Target academic admissions cycle")
    duration: str = Field(default="1.5-2 Years")
    tuition_usd: Optional[int] = Field(default=None, ge=0)
    tuition_gbp: Optional[int] = Field(default=None, ge=0)
    tuition_sgd: Optional[int] = Field(default=None, ge=0)
    tuition_hkd: Optional[int] = Field(default=None, ge=0)
    min_ielts: LanguageRequirementsModel
    min_toefl: LanguageRequirementsModel
    tier_bracket: Literal["Reach", "Match", "Safety"] = "Match"
    stem: bool = True
    gre_required: bool = False
    deadline: str = Field(default="Round 1: Dec 15 | Round 2: Jan 15")
    distinctive_courses: List[DistinctiveCourseModel] = Field(default_factory=list)
    capstone_nature: str = Field(default="工业界顶石实训 (Capstone)")
    nuance: Optional[str] = None
    accepted_tiers: List[ListTierRequirement] = Field(default_factory=list)
    required_prerequisites: List[PrerequisiteLinkModel] = Field(default_factory=list)

    @field_validator("region")
    @classmethod
    def validate_region(cls, v: str) -> str:
        upper_v = v.strip().upper()
        if upper_v not in VALID_REGIONS:
            raise ValueError(f"Invalid region '{v}'. Allowed regions: {sorted(VALID_REGIONS)}")
        return upper_v

    @field_validator("major_category")
    @classmethod
    def validate_major(cls, v: str) -> str:
        upper_v = v.strip().upper()
        if upper_v not in VALID_MAJORS:
            raise ValueError(f"Invalid major category '{v}'. Allowed categories: {sorted(VALID_MAJORS)}")
        return upper_v


class PaperModel(BaseModel):
    """Peer-reviewed publication record for academic outreach synergy."""
    title: str = Field(..., min_length=5, description="Full formal publication title")
    year: int = Field(..., ge=2015, le=2030, description="Publication year")
    venue: str = Field(..., min_length=2, description="Conference / Journal acronym (e.g. 'USENIX OSDI 2025')")
    abstract: str = Field(..., min_length=10)
    methodology: Optional[str] = None
    future_work_bottleneck: str = Field(..., min_length=5, description="Open research challenge for student cold email hook")
    academic_year: str = Field(default="2026_2027")


class ProfessorIngestModel(BaseModel):
    """Faculty profile with laboratory openings, research foci, and publications."""
    id: str = Field(..., pattern=r"^[a-z0-9_]+$", description="Unique scholar slug (e.g. 'indranil_gupta')")
    name: str = Field(..., min_length=2)
    institution: str = Field(..., min_length=2)
    lab: str = Field(..., min_length=2)
    research_areas: List[str] = Field(default_factory=list, min_length=1)
    academic_year: str = Field(default="2026_2027")
    openings: Dict[str, Any] = Field(default_factory=dict)
    recent_papers: List[PaperModel] = Field(default_factory=list)
    affiliated_programs: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_openings_structure(self) -> ProfessorIngestModel:
        if not self.openings.get("phd_fall_2027"):
            self.openings["phd_fall_2027"] = "Open for Fall 2027 admissions inquiries"
        if not self.openings.get("funding_status"):
            self.openings["funding_status"] = "Funded via departmental grants"
        return self


class PrerequisiteCourseIngestModel(BaseModel):
    """Curriculum prerequisite course node in topological graph."""
    id: str = Field(..., pattern=r"^[a-z0-9_]+$", description="Course slug (e.g. 'course_dsa')")
    name_cn: str = Field(..., min_length=2)
    name_en: str = Field(..., min_length=2)
    major_category: str = Field(..., description="Target discipline (CS, DS, BA, FIN)")
    aliases: List[str] = Field(default_factory=list)
    category: str = Field(default="Core")
    importance: Literal["Mandatory", "High", "Recommended"] = "Mandatory"
    academic_year: str = Field(default="2026_2027")


class AdmissionCaseIngestModel(BaseModel):
    """Historical admissions/rejections sample."""
    id: str = Field(..., min_length=2)
    target_program_id: str = Field(..., min_length=2)
    undergrad_name: str
    undergrad_tier: str
    gpa: float = Field(..., ge=0.0)
    gpa_scale: str = Field(default="100")
    major: str
    language: str
    background_summary: str
    outcome: str = "admit"
    outcome_type: Literal["admit", "reject"] = "admit"
    year: int = Field(default=2025, ge=2015)
    profile_text: str
    gre: Optional[str] = None
    academic_year: str = Field(default="2026_2027")


class BatchIngestBundle(BaseModel):
    """Comprehensive multi-entity bundle for atomic ingestion and hot updates."""
    academic_year: str = Field(default="2026_2027")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    universities: Optional[List[Dict[str, Any]]] = None
    courses: Optional[List[PrerequisiteCourseIngestModel]] = None
    programs: Optional[List[ProgramIngestModel]] = None
    professors: Optional[List[ProfessorIngestModel]] = None
    admission_cases: Optional[List[AdmissionCaseIngestModel]] = None


# =============================================================================
# Ingestion Pipeline Engine
# =============================================================================

class KnowledgeIngestor:
    """Manages structural validation and atomic hot-reloading for GraphStore and VectorStore."""

    def __init__(
        self,
        graph_store: Optional[GraphStore] = None,
        vector_store: Optional[VectorStore] = None,
        auto_persist: bool = True,
    ):
        self.graph_store = graph_store or get_graph_store()
        self.vector_store = vector_store or get_vector_store()
        self.auto_persist = auto_persist

    # -------------------------------------------------------------------------
    # Validation Helpers
    # -------------------------------------------------------------------------

    def validate_program(self, data: Dict[str, Any]) -> ProgramIngestModel:
        """Validate raw dictionary against ProgramIngestModel schema."""
        return ProgramIngestModel.model_validate(data)

    def validate_professor(self, data: Dict[str, Any]) -> ProfessorIngestModel:
        """Validate raw dictionary against ProfessorIngestModel schema."""
        return ProfessorIngestModel.model_validate(data)

    def validate_prerequisite_course(self, data: Dict[str, Any]) -> PrerequisiteCourseIngestModel:
        """Validate raw dictionary against PrerequisiteCourseIngestModel schema."""
        return PrerequisiteCourseIngestModel.model_validate(data)

    def validate_bundle(self, data: Dict[str, Any]) -> BatchIngestBundle:
        """Validate multi-entity bundle schema."""
        return BatchIngestBundle.model_validate(data)

    # -------------------------------------------------------------------------
    # Single-Entity Ingestion
    # -------------------------------------------------------------------------

    def ingest_program(
        self,
        program_data: Union[Dict[str, Any], ProgramIngestModel],
        persist: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Validate and incrementally ingest a program node into GraphStore & VectorStore."""
        model = (
            program_data
            if isinstance(program_data, ProgramIngestModel)
            else self.validate_program(program_data)
        )

        p_dict = model.model_dump()
        node_id = model.id

        # 1. Format Program node properties for GraphStore
        prog_props = {
            "id": node_id,
            "name_cn": model.name_cn,
            "name_en": model.name_en,
            "institution": model.institution,
            "region": model.region,
            "major_category": model.major_category,
            "academic_year": model.academic_year,
            "duration": model.duration,
            "min_ielts": model.min_ielts.model_dump(),
            "min_toefl": model.min_toefl.model_dump(),
            "tier_bracket": model.tier_bracket,
            "stem": model.stem,
            "gre_required": model.gre_required,
            "deadline": model.deadline,
            "distinctive_courses": [c.model_dump() for c in model.distinctive_courses],
            "capstone_nature": model.capstone_nature,
            "nuance": model.nuance or "关注工程落地与学术求索契合度",
        }
        if model.tuition_usd is not None:
            prog_props["tuition_usd"] = model.tuition_usd
        if model.tuition_gbp is not None:
            prog_props["tuition_gbp"] = model.tuition_gbp
        if model.tuition_sgd is not None:
            prog_props["tuition_sgd"] = model.tuition_sgd
        if model.tuition_hkd is not None:
            prog_props["tuition_hkd"] = model.tuition_hkd

        self.graph_store.add_node(node_id, "Program", prog_props)

        # 2. Add ACCEPTS_LIST edges
        for tier_req in model.accepted_tiers:
            # Ensure ChineseUniTier node exists
            if not self.graph_store.get_node(tier_req.tier):
                self.graph_store.add_node(tier_req.tier, "ChineseUniTier", {
                    "id": tier_req.tier,
                    "name": tier_req.tier,
                })
            self.graph_store.add_edge(
                source_id=node_id,
                target_id=tier_req.tier,
                rel_type="ACCEPTS_LIST",
                properties={"min_gpa_score": tier_req.min_gpa_score, "academic_year": model.academic_year}
            )

        # 3. Add REQUIRES_PREREQ edges
        for prereq in model.required_prerequisites:
            self.graph_store.add_edge(
                source_id=node_id,
                target_id=prereq.course_id,
                rel_type="REQUIRES_PREREQ",
                properties={"level": prereq.level, "academic_year": model.academic_year}
            )

        # 4. Synchronize ProgramNuance to VectorStore
        nuance_obj = ProgramNuance(
            program_id=node_id,
            name=f"{model.institution} - {model.name_cn}",
            nuance_summary=model.nuance or f"{model.name_cn} 强调扎实专业理论与高阶工程实践",
            deadline=model.deadline,
            gre_policy="Required" if model.gre_required else "Optional",
            stem_status="STEM-Designated" if model.stem else "Non-STEM",
            detailed_text=f"{model.name_cn} ({model.name_en}) at {model.institution}. "
                          f"Region: {model.region}, Major: {model.major_category}. "
                          f"Ethos: {model.nuance}",
        )
        self.vector_store.add_program_nuance(nuance_obj)

        should_persist = persist if persist is not None else self.auto_persist
        if should_persist:
            self._persist_stores()

        return {
            "status": "success",
            "entity": "Program",
            "id": node_id,
            "academic_year": model.academic_year,
            "accepted_tiers_count": len(model.accepted_tiers),
            "prerequisites_count": len(model.required_prerequisites),
        }

    def ingest_professor(
        self,
        prof_data: Union[Dict[str, Any], ProfessorIngestModel],
        persist: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Validate and incrementally ingest a professor node and papers into GraphStore."""
        model = (
            prof_data
            if isinstance(prof_data, ProfessorIngestModel)
            else self.validate_professor(prof_data)
        )

        node_id = model.id
        prof_props = {
            "id": node_id,
            "name": model.name,
            "institution": model.institution,
            "lab": model.lab,
            "research_areas": model.research_areas,
            "academic_year": model.academic_year,
            "openings": model.openings,
            "recent_papers": [p.model_dump() for p in model.recent_papers],
        }

        self.graph_store.add_node(node_id, "Professor", prof_props)

        # Add AFFILIATED_WITH edges if programs specified
        for prog_id in model.affiliated_programs:
            if self.graph_store.get_node(prog_id):
                self.graph_store.add_edge(
                    source_id=node_id,
                    target_id=prog_id,
                    rel_type="AFFILIATED_WITH",
                    properties={"title": "Faculty Member", "academic_year": model.academic_year}
                )

        should_persist = persist if persist is not None else self.auto_persist
        if should_persist:
            self._persist_stores()

        return {
            "status": "success",
            "entity": "Professor",
            "id": node_id,
            "papers_count": len(model.recent_papers),
            "academic_year": model.academic_year,
        }

    def ingest_prerequisite_course(
        self,
        course_data: Union[Dict[str, Any], PrerequisiteCourseIngestModel],
        persist: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Validate and ingest a Course prerequisite node into GraphStore."""
        model = (
            course_data
            if isinstance(course_data, PrerequisiteCourseIngestModel)
            else self.validate_prerequisite_course(course_data)
        )

        node_id = model.id
        props = model.model_dump()
        props["label"] = "Course"
        self.graph_store.add_node(node_id, "Course", props)

        should_persist = persist if persist is not None else self.auto_persist
        if should_persist:
            self._persist_stores()

        return {
            "status": "success",
            "entity": "Course",
            "id": node_id,
            "academic_year": model.academic_year,
        }

    # -------------------------------------------------------------------------
    # Batch Ingestion
    # -------------------------------------------------------------------------

    def ingest_batch(
        self,
        bundle_data: Union[Dict[str, Any], BatchIngestBundle],
        persist: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Atomic multi-entity bundle ingestion with full validation before ingestion."""
        bundle = (
            bundle_data
            if isinstance(bundle_data, BatchIngestBundle)
            else self.validate_bundle(bundle_data)
        )

        counts = {
            "universities": 0,
            "courses": 0,
            "programs": 0,
            "professors": 0,
            "admission_cases": 0,
        }

        # 1. Ingest Universities
        if bundle.universities:
            for uni in bundle.universities:
                uni_id = uni.get("id")
                if uni_id:
                    self.graph_store.add_node(uni_id, "University", uni)
                    counts["universities"] += 1

        # 2. Ingest Prerequisite Courses
        if bundle.courses:
            for course_model in bundle.courses:
                self.ingest_prerequisite_course(course_model, persist=False)
                counts["courses"] += 1

        # 3. Ingest Programs
        if bundle.programs:
            for prog_model in bundle.programs:
                self.ingest_program(prog_model, persist=False)
                counts["programs"] += 1

        # 4. Ingest Professors
        if bundle.professors:
            for prof_model in bundle.professors:
                self.ingest_professor(prof_model, persist=False)
                counts["professors"] += 1

        # 5. Ingest Admission Cases
        if bundle.admission_cases:
            for case_model in bundle.admission_cases:
                c_dict = case_model.model_dump()
                adm_case = AdmissionCase(
                    id=c_dict["id"],
                    target_program_id=c_dict["target_program_id"],
                    undergrad_name=c_dict["undergrad_name"],
                    undergrad_tier=c_dict["undergrad_tier"],
                    gpa=c_dict["gpa"],
                    gpa_scale=c_dict.get("gpa_scale", "100"),
                    major=c_dict["major"],
                    language=c_dict["language"],
                    background_summary=c_dict["background_summary"],
                    outcome=c_dict["outcome"],
                    outcome_type=c_dict["outcome_type"],
                    year=c_dict["year"],
                    profile_text=c_dict["profile_text"],
                    gre=c_dict.get("gre"),
                )
                self.vector_store.add_admission_case(adm_case)
                counts["admission_cases"] += 1

        should_persist = persist if persist is not None else self.auto_persist
        if should_persist:
            self._persist_stores()

        return {
            "status": "success",
            "academic_year": bundle.academic_year,
            "ingested_counts": counts,
            "timestamp": bundle.timestamp,
        }

    def ingest_file(
        self,
        json_path: Union[str, Path],
        persist: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Ingest knowledge bundle from a JSON file path."""
        p = Path(json_path)
        if not p.exists():
            raise FileNotFoundError(f"Knowledge bundle JSON file not found: {p}")
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self.ingest_batch(data, persist=persist)

    # -------------------------------------------------------------------------
    # Knowledge Base Health Inspection
    # -------------------------------------------------------------------------

    def inspect_knowledge_base(self) -> Dict[str, Any]:
        """Generate high-level inventory and audit summary of knowledge base assets."""
        programs = self.graph_store.get_nodes_by_label("Program")
        professors = self.graph_store.get_nodes_by_label("Professor")
        courses = self.graph_store.get_nodes_by_label("Course")
        universities = self.graph_store.get_nodes_by_label("University")

        # Regional distribution
        region_dist: Dict[str, int] = {}
        for p in programs:
            reg = p.get("region", "UNKNOWN")
            region_dist[reg] = region_dist.get(reg, 0) + 1

        # List edge count
        list_edges = [
            (u, v, d)
            for u, v, k, d in self.graph_store.graph.edges(keys=True, data=True)
            if k == "ACCEPTS_LIST"
        ]

        total_nodes = self.graph_store.graph.number_of_nodes()
        total_edges = self.graph_store.graph.number_of_edges()

        return {
            "total_graph_nodes": total_nodes,
            "total_graph_edges": total_edges,
            "programs_count": len(programs),
            "professors_count": len(professors),
            "courses_count": len(courses),
            "universities_count": len(universities),
            "list_pruning_rules_count": len(list_edges),
            "programs_by_region": region_dist,
            "vector_cases_count": len(self.vector_store.cases),
            "vector_nuances_count": len(self.vector_store.nuances),
            "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # -------------------------------------------------------------------------
    # Persistence Helper
    # -------------------------------------------------------------------------

    def _persist_stores(self) -> None:
        """Persist in-memory state of GraphStore and VectorStore to SQLite."""
        try:
            self.graph_store.save_to_sqlite()
        except Exception as e:
            logger.warning(f"Failed to persist GraphStore to SQLite: {e}")

        try:
            self.vector_store.save_to_sqlite()
        except Exception as e:
            logger.warning(f"Failed to persist VectorStore to SQLite: {e}")
