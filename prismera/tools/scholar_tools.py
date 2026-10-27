"""Scholar publication search and lab opening inspection tools for prism_resonator."""

from __future__ import annotations
from typing import Dict, Any, List, Optional


SCHOLARS_DB = {
    "indranil_gupta": {
        "name": "Indranil Gupta",
        "institution": "UIUC (Department of Computer Science)",
        "lab": "Distributed Protocols Research Group (DPRG)",
        "openings": {
            "phd_fall_2027": "Open (2 funded positions available for candidates with strong distributed systems or cloud telemetry background)",
            "ra_positions": "Open for enrolled graduate students",
            "funding_status": "Fully funded via NSF Large-Scale Cloud Grant and industrial sponsorship",
            "lab_page": "https://dprg.cs.uiuc.edu"
        },
        "recent_papers": [
            {
                "title": "Adaptive Gossip Consensus in Latency-Asymmetric Edge Meshes",
                "year": 2025,
                "venue": "USENIX OSDI 2025",
                "abstract": "We explore gossip-based peer membership in non-uniform WAN edge networks. When packet loss exceeds 12%, traditional failure detectors induce cascading heartbeat storms.",
                "methodology": "Constructed an event-driven C++ simulation harness coupled with an eBPF kernel network throttle to evaluate convergence delay under Byzantine drops.",
                "future_work_bottleneck": "Scalable membership convergence under highly partitioned topologies and ultra-sparse heartbeat feedback remains an open scalability barrier."
            },
            {
                "title": "Hierarchical Straggler Mitigation in Heterogeneous ML Accelerators",
                "year": 2024,
                "venue": "IEEE S&P / Distributed Systems",
                "abstract": "Investigated GPU tensor streaming bottlenecks across mixed PCIe and NVLink topologies during distributed mixture-of-experts (MoE) training.",
                "methodology": "Profiling PyTorch distributed collectives with custom CUDA telemetry hooks.",
                "future_work_bottleneck": "Dynamic gradient chunking under bursty network contention."
            }
        ]
    },
    "david_garlan": {
        "name": "David Garlan",
        "institution": "Carnegie Mellon University (Software and Societal Systems)",
        "lab": "ABLE Research Group (Self-Adaptive Software Systems)",
        "openings": {
            "phd_fall_2027": "Open (1 funded PhD student in Autonomous Systems Verification)",
            "ra_positions": "Limited Master's research assistantships",
            "funding_status": "Active DARPA and NSF awards",
            "lab_page": "https://able.cs.cmu.edu"
        },
        "recent_papers": [
            {
                "title": "Formal Architecture Models for Uncertainty-Aware Autonomous Systems",
                "year": 2025,
                "venue": "ACM Transactions on Software Engineering and Methodology (TOSEM)",
                "abstract": "Self-adaptive software architectures must reason over stochastic sensor noise and adversarial drift without re-verifying full state spaces at runtime.",
                "methodology": "Combined probabilistic model checking (PRISM) with reactive architectural feedback loops.",
                "future_work_bottleneck": "Reducing runtime verification latency down to millisecond thresholds for safety-critical edge robotics."
            }
        ]
    }
}


def fetch_scholar_recent_papers(
    scholar_name: str,
    institution: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Fetch core research papers published in the last 3 years by the target scholar."""
    norm_name = scholar_name.lower().replace(".", "").replace(" ", "_").strip()

    for key, data in SCHOLARS_DB.items():
        if norm_name in key or key in norm_name:
            return data["recent_papers"]

    # If not found in local mock cache, return empty list to trigger the honest fallback rule
    # (reserving academic integrity as demanded by the prompt)
    return []


def inspect_lab_openings(
    scholar_name: str,
    institution: Optional[str] = None
) -> Dict[str, Any]:
    """Inspect prospective student openings and funding status for the professor's laboratory."""
    norm_name = scholar_name.lower().replace(".", "").replace(" ", "_").strip()

    for key, data in SCHOLARS_DB.items():
        if norm_name in key or key in norm_name:
            return {
                "scholar_name": data["name"],
                "institution": data["institution"],
                "lab_name": data["lab"],
                **data["openings"]
            }

    return {
        "scholar_name": scholar_name,
        "institution": institution or "Target Institution",
        "lab_name": "Research Group",
        "phd_fall_2027": "待官方邮件或导师主页更新确认",
        "funding_status": "建议在套磁信中主动礼貌询问",
        "lab_page": "https://scholar.google.com"
    }
