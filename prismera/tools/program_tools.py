"""Program ethos, course syllabus, and faculty lab retriever for prism_disperser.

Queries GraphStore for program mission ethos, distinctive courses, and faculty leads.
"""

from __future__ import annotations
from typing import Dict, Any

from prismera.db.graph_store import get_graph_store

PROGRAM_ETHOS_DB: Dict[str, Any] = {}


def get_program_ethos_and_courses(program_id: str) -> Dict[str, Any]:
    """Retrieve program mission ethos, distinctive course codes, and capstone features."""
    gs = get_graph_store()
    prog_node = gs.get_node(program_id)

    if prog_node:
        # Find university node
        uni_name = "Target University"
        uni_edges = gs.get_outgoing_edges(program_id, rel_type="OFFERED_BY")
        if uni_edges:
            uni_node = gs.get_node(uni_edges[0]["target"])
            if uni_node:
                uni_name = uni_node.get("name_en", uni_node.get("name_cn", "Target University"))
        elif "university_id" in prog_node:
            uni_node = gs.get_node(prog_node["university_id"])
            if uni_node:
                uni_name = uni_node.get("name_en", uni_node.get("name_cn", "Target University"))

        # Find affiliated faculty leads
        faculty_leads = prog_node.get("faculty_leads", [])
        if not faculty_leads:
            prof_edges = gs.get_incoming_edges(program_id, rel_type="AFFILIATED_WITH")
            for pe in prof_edges:
                prof_node = gs.get_node(pe["source"])
                if prof_node and "name" in prof_node:
                    faculty_leads.append(f"Prof. {prof_node['name']}")

        return {
            "institution": uni_name,
            "program": prog_node.get("name_en", prog_node.get("name_cn", "Graduate Program")),
            "mission_ethos": prog_node.get(
                "mission_ethos",
                "Cultivating pioneering researchers and engineering leaders through foundational theory and interdisciplinary project collaboration."
            ),
            "distinctive_courses": prog_node.get("distinctive_courses", [
                {"code": "CS 601", "title": "Advanced Algorithms and Complexity", "focus": "NP-completeness, randomized algorithms"}
            ]),
            "capstone_nature": prog_node.get(
                "capstone_nature",
                "Independent graduate research project or industry capstone."
            ),
            "faculty_leads": faculty_leads or ["Core Department Faculty"]
        }

    return {
        "institution": "Target University",
        "program": "Master of Science in Computer Science",
        "mission_ethos": "Cultivating pioneering researchers and engineering leaders through foundational theory and interdisciplinary project collaboration.",
        "distinctive_courses": [
            {"code": "CS 601", "title": "Advanced Algorithms and Complexity", "focus": "NP-completeness, randomized algorithms"},
            {"code": "CS 620", "title": "Distributed Storage and Cloud Architectures", "focus": "Consistency models, microservices orchestration"}
        ],
        "capstone_nature": "Independent graduate research project or industry capstone.",
        "faculty_leads": ["Core Department Faculty"]
    }
