"""Program ethos, course syllabus, and faculty lab retriever for prism_disperser."""

from __future__ import annotations
from typing import Dict, Any


PROGRAM_ETHOS_DB = {
    "cmu_msit_se": {
        "institution": "Carnegie Mellon University",
        "program": "Master of Science in Information Technology - Software Engineering (MSIT-SE)",
        "mission_ethos": "Bridging rigorous systems software architecture with agile enterprise delivery; emphasizes scalable distributed engineering, testing pipelines, and real-client capstone execution.",
        "distinctive_courses": [
            {"code": "17-651", "title": "Models of Software Systems", "focus": "Formal specification, invariants, and structural abstraction"},
            {"code": "17-652", "title": "Methods: Deciding What to Design", "focus": "Requirements engineering and architectural tradeoff analysis"},
            {"code": "17-653", "title": "Managing Software Development", "focus": "Agile team dynamics, CI/CD observability, defect velocity"}
        ],
        "capstone_nature": "Year-long industry-sponsored Practicum under dedicated executive mentorship.",
        "faculty_leads": ["Prof. David Garlan", "Prof. Mary Shaw"]
    },
    "uiuc_mcs": {
        "institution": "University of Illinois Urbana-Champaign",
        "program": "Master of Computer Science (MCS)",
        "mission_ethos": "Theoretical rigor coupled with high-throughput cloud infrastructure and algorithmic problem solving; ideal for students targeting tier-1 software research or deep engineering.",
        "distinctive_courses": [
            {"code": "CS 425", "title": "Distributed Systems", "focus": "Consensus protocols, Raft/Paxos, fault-tolerant replication"},
            {"code": "CS 440", "title": "Artificial Intelligence", "focus": "Probabilistic graphical models and heuristic search"},
            {"code": "CS 525", "title": "Advanced Distributed Systems", "focus": "P2P overlays, geo-distributed transactions, zero-trust topologies"}
        ],
        "capstone_nature": "Advanced coursework-driven with options for high-performance computing practicum.",
        "faculty_leads": ["Prof. Indranil Gupta", "Prof. Klara Nahrstedt"]
    },
    "ic_computing_msc": {
        "institution": "Imperial College London",
        "program": "MSc Computing Science",
        "mission_ethos": "Rigorous European engineering foundation emphasizing mathematical correctness, machine intelligence, and systems verification.",
        "distinctive_courses": [
            {"code": "COMP70015", "title": "Mathematics for Machine Learning", "focus": "Matrix calculus, convex optimization, kernel methods"},
            {"code": "COMP70016", "title": "Scalable Systems and Data", "focus": "Stream processing, memory hierarchy caching, distributed schedulers"}
        ],
        "capstone_nature": "Individual research thesis defended before a faculty tribunal in September.",
        "faculty_leads": ["Prof. William Knottenbelt", "Prof. Stefanos Zafeiriou"]
    }
}


def get_program_ethos_and_courses(program_id: str) -> Dict[str, Any]:
    """Retrieve program mission ethos, distinctive course codes, and capstone features."""
    return PROGRAM_ETHOS_DB.get(program_id, {
        "institution": "Target University",
        "program": "Master of Science in Computer Science",
        "mission_ethos": "Cultivating pioneering researchers and engineering leaders through foundational theory and interdisciplinary project collaboration.",
        "distinctive_courses": [
            {"code": "CS 601", "title": "Advanced Algorithms and Complexity", "focus": "NP-completeness, randomized algorithms"},
            {"code": "CS 620", "title": "Distributed Storage and Cloud Architectures", "focus": "Consistency models, microservices orchestration"}
        ],
        "capstone_nature": "Independent graduate research project or industry capstone.",
        "faculty_leads": ["Core Department Faculty"]
    })
