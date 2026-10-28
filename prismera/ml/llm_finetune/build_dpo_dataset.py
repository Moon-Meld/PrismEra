"""Builder for Prism-DeAI Essay DPO (Direct Preference Optimization) Dataset.

Constructs preference alignment datasets in HuggingFace TRL (DPOTrainer) and
LLaMA-Factory standard format:
  {"prompt": "...", "chosen": "...", "rejected": "..."}

- `chosen`: Grounded, Show-Don't-Tell human-style paragraphs with concrete metrics,
  specific course codes, active engineering verbs, and ZERO banned AI clichés.
- `rejected`: Plastic, cliché-heavy AI outputs featuring "delve into", "rich tapestry",
  "unwavering passion", "transformative journey", "beacon of hope", etc.
"""

from __future__ import annotations
import argparse
import json
import os
import random
from pathlib import Path
from typing import Dict, Any, List, Tuple

from prismera.guardrails import AntiAIGuardrail

DOMAINS = [
    {
        "field": "Distributed Systems",
        "schools": [
            ("Carnegie Mellon University", "MS in Information Technology - Software Engineering (MSIT-SE)", "17-651 (Models of Software Systems)", "Prof. David Garlan"),
            ("Stanford University", "MS in Computer Science (Systems Track)", "CS 244B (Distributed Systems)", "Prof. John Ousterhout"),
            ("University of Washington", "MS in Computer Science & Engineering", "CSE 552 (Distributed Systems)", "Prof. Arvind Krishnamurthy"),
        ],
        "project_templates": [
            ("Raft-replicated key-value store with sharded RPC consensus", "34% tail latency reduction under 10,000 QPS load", "multi-threaded lock contention across asynchronous gRPC channels"),
            ("LSM-Tree persistent storage engine with tiered compaction", "4.2x write amplification mitigation on NVMe storage", "write stall spikes caused by concurrent background flush operations"),
            ("Distributed transactional coordinator based on 2-Phase Commit and Paxos", "99.99% atomic commit consistency during network partitions", "split-brain anomalies during transient leader lease expirations"),
        ],
        "chosen_templates": [
            "In engineering our {project}, I resolved {bottleneck}, achieving {metric}. When scaling the benchmark cluster across 8 nodes, I refactored the concurrent ring buffer to avoid lock contention. At {school}'s {program}, I intend to build upon this empirical systems foundation through {course}, formalizing distributed invariants under the guidance of {faculty}.",
            "During my work on {project}, I profiled memory access patterns to address {bottleneck}. This optimization resulted in {metric} while maintaining zero read regression. In {school}'s {program}, I look forward to taking {course} and working with {faculty} to investigate fault-tolerant protocol verification.",
        ],
        "rejected_templates": [
            "My unwavering passion for software engineering has inspired me to delve into the rich tapestry of {project}, delivering {metric}. This transformative journey was a testament to my dedication, illuminating the pivotal realm of computer science. At {school}, I yearn to embark on this journey and deep dive into {course}.",
            "Ever since I ignited my interest in systems, I have embarked on a transformative journey to delve into {project}, producing {metric}. This endeavor stands as a shining testament to my unwavering passion. At {school}, I desire to immerse myself in the rich tapestry of research under {faculty}.",
        ],
    },
    {
        "field": "Machine Learning & NLP",
        "schools": [
            ("Imperial College London", "MSc Computing (Artificial Intelligence & Machine Learning)", "COMP70015 (Deep Learning)", "Prof. Francesca Toni"),
            ("National University of Singapore", "Master of Computing (Artificial Intelligence)", "CS5242 (Advanced Neural Networks)", "Prof. Min-Yen Kan"),
            ("University of Edinburgh", "MSc in Artificial Intelligence", "INFR11133 (Natural Language Understanding)", "Prof. Mirella Lapata"),
        ],
        "project_templates": [
            ("low-rank adaptation (LoRA) quantization framework for 7B-parameter LLMs", "1.8x inference throughput acceleration on consumer GPUs", "quadratic attention memory footprint during long-context generation"),
            ("cross-lingual contrastive representation retrieval model for low-resource dialects", "8.6 BLEU score improvement across 6 Indic languages", "semantic drift caused by scarce aligned parallel corpora"),
            ("reinforcement learning with human feedback (RLHF) preference boundary tuner", "23% reduction in reward hacking and length bias", "overfitting on superficial stylistic markers rather than factual correctness"),
        ],
        "chosen_templates": [
            "To address {bottleneck} in our {project}, I designed a dynamic rank-allocation scheduler that achieved {metric}. Profiling the backward gradient propagation revealed that unfreezing key projection heads preserved cross-attention fidelity. At {school}'s {program}, I plan to expand this line of inquiry through {course} with {faculty}.",
            "Working on {project}, I tackled {bottleneck}. By curating an adversarial verification benchmark, our pipeline demonstrated {metric}. I am eager to join {school}'s {program} to examine robust representation learning in {course} mentored by {faculty}.",
        ],
        "rejected_templates": [
            "Driven by an unwavering passion for artificial intelligence, I sought to delve into the multifaceted tapestry of {project}, attaining {metric}. This transformative journey underscored my pivotal role in pushing technological frontiers. Joining {school} will be a beacon of hope where I can deep dive into {course}.",
            "My journey in natural language processing ignited my interest to embark on the breathtaking realm of {project}, showing {metric}. It served as an undeniable testament to my unwavering passion. At {school}, I yearn to delve into the symphony of machine intelligence with {faculty}.",
        ],
    },
    {
        "field": "Quantitative Finance & Analytics",
        "schools": [
            ("Columbia University", "MS in Financial Engineering (MSFE)", "IEOR E4706 (Financial Engineering I)", "Prof. Emanuel Derman"),
            ("New York University", "MS in Mathematics in Finance (Courant)", "MATH-GA 2791 (Derivative Securities)", "Prof. Peter Carr"),
            ("University College London", "MSc Computational Finance", "COMP0043 (Numerical Methods for Finance)", "Prof. Guido Germano"),
        ],
        "project_templates": [
            ("high-frequency order book dynamics and market impact simulator", "15% improvement in Out-of-Sample Sharpe ratio", "adverse selection risk during flash liquidity droughts"),
            ("stochastic volatility calibration engine using rough Heston models", "45% reduction in numerical PDE solving time", "slow convergence of classical Monte Carlo finite difference grids"),
            ("cross-asset statistical arbitrage pipeline with risk parity overlay", "maximum drawdown containment within 4.8% during regime shifts", "correlated breakdown of cointegration pairs under macroeconomic shocks"),
        ],
        "chosen_templates": [
            "When developing the {project}, I mitigated {bottleneck} by reformulating the volatility surface using jump-diffusion kernels, producing {metric}. Backtesting across five years of tick-level L2 data validated execution stability. At {school}, {program} will enable me to study {course} and calibrate stochastic models with {faculty}.",
            "My implementation of {project} targeted {bottleneck}. By replacing naive gradient descent with sparse matrix solvers, the engine yielded {metric}. I am keen to study in {school}'s {program}, specifically taking {course} to deepen my mathematical rigor under {faculty}.",
        ],
        "rejected_templates": [
            "With an unwavering passion for mathematical finance, I embarked on a journey to delve into the intricate tapestry of {project}, yielding {metric}. This transformative endeavor became a testament to my dedication to navigating complex markets. {school}'s {program} is the pivotal realm where I will deep dive into {course}.",
            "Quantitative finance has ignited my interest to explore the rich tapestry of financial markets. Developing {project} was a transformative journey that brought {metric}. At {school}, I wish to delve into the symphony of asset pricing with {faculty}.",
        ],
    },
    {
        "field": "Robotics & Computer Vision",
        "schools": [
            ("University of Michigan", "MS in Robotics", "ROB 550 (Robotics Systems Laboratory)", "Prof. Jessy Grizzle"),
            ("ETH Zurich", "Master in Robotics, Systems and Control", "151-0851-00L (Robot Dynamics)", "Prof. Marco Hutter"),
            ("University of Pennsylvania", "MSE in Robotics (Robomaster)", "MEAM 620 (Advanced Robotics)", "Prof. Vijay Kumar"),
        ],
        "project_templates": [
            ("visual-inertial SLAM state estimation system for quadrotors in GPS-denied environments", "sub-5cm trajectory drift over a 200m underground trajectory", "scale drift caused by rapid illumination changes and feature dropout"),
            ("model predictive control (MPC) locomotion controller for quadrupedal robots", "stable traversal over 30-degree slippery rubble slopes", "actuator saturation and foot slip during sudden terrain elevation transitions"),
            ("real-time 3D semantic Gaussian splatting for dynamic scene reconstruction", "real-time 60 FPS rendering with 32.4 dB PSNR", "floating artifacts and high VRAM overhead in unconstrained outdoor scenes"),
        ],
        "chosen_templates": [
            "To counter {bottleneck} while building our {project}, I integrated an extended Kalman filter with optical flow priors, achieving {metric}. Testing the pipeline on onboard Jetson Orin hardware proved real-time determinism. At {school}, {program} offers the ideal environment to pursue {course} alongside {faculty}.",
            "In our deployment of {project}, I focused on eliminating {bottleneck}. Formulating the quadratic program using sparse QP solvers enabled {metric}. I am eager to join {school}'s {program} to investigate whole-body dynamics in {course} with {faculty}.",
        ],
        "rejected_templates": [
            "Robotics is a rich tapestry of engineering where my unwavering passion has found its home. Embarking on a transformative journey with {project}, I reached {metric} and delved into the profound depths of autonomous systems. Joining {school} is my beacon of hope to deep dive into {course}.",
            "My fascination with robotic intelligence ignited my interest to delve into the vibrant tapestry of {project}, reaching {metric}. This journey was a testament to my tireless commitment. At {school}, I aspire to embark on this pivotal realm under the mentorship of {faculty}.",
        ],
    },
    {
        "field": "Data Science & Cloud Infrastructure",
        "schools": [
            ("New York University", "MS in Data Science (Center for Data Science)", "DS-GA 1008 (Deep Learning)", "Prof. Yann LeCun"),
            ("Columbia University", "MS in Data Science", "COMS W4995 (Applied Machine Learning)", "Prof. Andreas Mueller"),
            ("University of California, San Diego", "MS in Computer Science (Database Track)", "CSE 232A (Database System Principles)", "Prof. Alin Deutsch"),
        ],
        "project_templates": [
            ("distributed stream processing pipeline using Apache Flink and Kafka", "sub-10ms end-to-end event latency at 500,000 events/second", "backpressure accumulation during irregular upstream network bursts"),
            ("heterogeneous graph neural network for financial transaction fraud detection", "14.2% precision increase at 99% recall on 10M credit records", "severe topological imbalance between benign accounts and sparse illicit rings"),
            ("cloud-native serverless ML model inference autoscaler on Kubernetes", "40% cloud compute billing reduction while meeting 100ms SLOs", "cold-start latency spikes when scaling zero-replica microservices"),
        ],
        "chosen_templates": [
            "In building the {project}, I resolved {bottleneck} by implementing adaptive credit-based windowing, reaching {metric}. I profiled Linux network socket buffers to minimize context switches. In {school}'s {program}, I aim to leverage {course} to further investigate distributed query optimization under {faculty}.",
            "Addressing {bottleneck} during the development of {project}, I introduced an embedding distillation technique that secured {metric}. I look forward to enrolling in {school}'s {program} to examine data-intensive computing in {course} with {faculty}.",
        ],
        "rejected_templates": [
            "Data science is a rich tapestry that ignited my interest in the digital age. Embarking on {project}, I achieved {metric} and delved into data engineering with unwavering passion. This transformative journey was a testament to my perseverance. At {school}, I yearn to deep dive into {course}.",
            "My unwavering passion has driven me to delve into {project}, obtaining {metric} and uncovering the rich tapestry of modern big data. This endeavor stands as a shining testament to my ambition. At {school}, I hope to embark on this pivotal realm and explore {course} with {faculty}.",
        ],
    },
]

PROMPT_CONTEXT_TEMPLATES = [
    "学生背景：{tier}院校 {major}专业，GPA {gpa}。核心经历：参与{project}，攻坚重点为{bottleneck}，最终达成{metric}。申请目标：{school}的 {program} 个人陈述（PS）核心段落，拟修读课程 {course} 并对接 {faculty} 的研究方向。请以棱镜纪【去AI化 / Show-Don't-Tell】标准撰写一段严谨、高信噪比的文书学术叙事段落。",
    "申请者画像：本科毕业于{tier}学府（均分 {gpa}），攻读{major}。在科研/工程实践中主导完成{project}，核心成果包括{metric}，有效化解了{bottleneck}。请为该学生定制申请 {school}（项目：{program}）的学术动机阐述段，融入课程 {course} 与导师 {faculty}，注重硬核工程细节与因果推演。",
]

PROMPT_WITHOUT_METRIC_TEMPLATES = [
    "学生背景：{tier}院校 {major}专业，GPA {gpa}。核心经历：参与{project}，攻坚重点为{bottleneck}（注：履历初稿中尚未提供实验实测指标与压测数据）。申请目标：{school}的 {program} 个人陈述（PS）段落，拟修读课程 {course} 并对接 {faculty}。要求：必须坚持事实忠实度，严禁凭空捏造虚假性能数字；若缺乏确切数据，必须使用 [METRIC: ...] 结构化证据槽位进行留白标注。",
    "申请者画像：本科毕业于{tier}学府（均分 {gpa}），攻读{major}。科研实践中完成{project}，攻关核心为{bottleneck}。目前未掌握确切量化成果数据。请为申请 {school}（{program}）撰写学术阐述段，融入课程 {course} 与导师 {faculty}。严禁伪造量化指标，缺失处需预留结构化证据槽位供学生后续核实填入。",
]

STRUCTURED_SLOTS = [
    "[METRIC: 填入吞吐量提升%与压测基准]",
    "[METRIC: 填入实测延迟降低%与并发倍数]",
    "[METRIC: 填入模型精度BLEU/Sharpe比提升幅度]",
    "[METRIC: 待补填实测误差减小%与收敛加速比]",
    "[METRIC: 填入帧率FPS提升与显存节约%]",
]

STUDENT_TIERS = ["国内顶尖C9", "985工程重点", "211工程骨干", "Top 50海外本科", "双非卓越一本"]
GPAS = ["3.85/4.0", "3.78/4.0", "3.91/4.0", "88.5/100", "91.2/100", "3.72/4.0"]


def build_dpo_sample(seed_idx: int) -> Dict[str, str]:
    """Construct a single high-quality DPO preference sample.
    
    Milestone 4.8 Anti-Hallucination Upgrade:
    - If input prompt lacks explicit experimental metrics, `chosen` MUST use structured
      evidence slots (e.g. `[METRIC: 填入吞吐量提升%]`) rather than fabricating fake numbers.
    - `rejected` hallucinates ungrounded numbers or uses empty AI clichés.
    """
    domain = DOMAINS[seed_idx % len(DOMAINS)]
    school, program, course, faculty = random.choice(domain["schools"])
    project, default_metric, bottleneck = random.choice(domain["project_templates"])
    tier = random.choice(STUDENT_TIERS)
    gpa = random.choice(GPAS)
    major = domain["field"]

    # 50% samples have explicit metrics in prompt; 50% omit them to enforce structured slots
    has_explicit_metric = (seed_idx % 2 == 0)

    if has_explicit_metric:
        metric = default_metric
        prompt_tpl = random.choice(PROMPT_CONTEXT_TEMPLATES)
        prompt = prompt_tpl.format(
            tier=tier,
            major=major,
            gpa=gpa,
            project=project,
            metric=metric,
            bottleneck=bottleneck,
            school=school,
            program=program,
            course=course,
            faculty=faculty,
        )
        chosen_metric = metric
        rejected_metric = metric
    else:
        prompt_tpl = random.choice(PROMPT_WITHOUT_METRIC_TEMPLATES)
        prompt = prompt_tpl.format(
            tier=tier,
            major=major,
            gpa=gpa,
            project=project,
            bottleneck=bottleneck,
            school=school,
            program=program,
            course=course,
            faculty=faculty,
        )
        # Anti-Hallucination: Chosen uses structured evidence slot
        chosen_metric = random.choice(STRUCTURED_SLOTS)
        # Baseline/Rejected hallucinates made-up metrics out of thin air
        rejected_metric = f"{random.randint(88, 99)}.{random.randint(1, 9)}% astonishing breakthrough"

    chosen_tpl = random.choice(domain["chosen_templates"])
    chosen = chosen_tpl.format(
        project=project,
        bottleneck=bottleneck,
        metric=chosen_metric,
        school=school,
        program=program,
        course=course,
        faculty=faculty,
    )

    rejected_tpl = random.choice(domain["rejected_templates"])
    rejected = rejected_tpl.format(
        project=project,
        bottleneck=bottleneck,
        metric=rejected_metric,
        school=school,
        program=program,
        course=course,
        faculty=faculty,
    )

    # Post-validation: Chosen MUST have 0 banned words
    guardrail = AntiAIGuardrail()
    chosen_violations = guardrail.scan(chosen)
    if chosen_violations:
        chosen = guardrail.rewrite_deterministic(chosen, chosen_violations)

    # Rejected MUST have banned words
    rejected_violations = guardrail.scan(rejected)
    if not rejected_violations:
        rejected = f"With unwavering passion, I delve into the rich tapestry of this field. {rejected}"

    return {
        "prompt": prompt,
        "chosen": chosen,
        "rejected": rejected,
    }


def generate_dpo_dataset(
    output_path: str = "data/finetune/disperser_dpo_train.jsonl",
    num_samples: int = 300,
    seed: int = 42,
) -> List[Dict[str, str]]:
    """Generate and write DPO dataset to disk."""
    random.seed(seed)
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    samples: List[Dict[str, str]] = []
    guardrail = AntiAIGuardrail()

    for idx in range(num_samples):
        sample = build_dpo_sample(idx)
        # Verify guardrails
        assert len(guardrail.scan(sample["chosen"])) == 0, f"Chosen contains banned words at index {idx}"
        assert len(guardrail.scan(sample["rejected"])) > 0, f"Rejected missing banned words at index {idx}"
        samples.append(sample)

    with open(out_file, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    return samples


def main():
    parser = argparse.ArgumentParser(description="PrismEra DPO Dataset Builder")
    parser.add_argument(
        "--output",
        type=str,
        default="data/finetune/disperser_dpo_train.jsonl",
        help="Target output JSONL path",
    )
    parser.add_argument(
        "--num_samples",
        type=int,
        default=300,
        help="Number of DPO pairs to synthesize",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    samples = generate_dpo_dataset(
        output_path=args.output,
        num_samples=args.num_samples,
        seed=args.seed,
    )
    print(f"Successfully generated {len(samples)} DPO pairs -> {args.output}")


if __name__ == "__main__":
    main()
