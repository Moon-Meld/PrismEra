"""Interview question bank, dynamic answer evaluation, and application timeline tools for prism_echo (The Echo).

Supports Kira video machine interviews, alumni behavioral interviews, and professor technical interviews,
alongside precise timeline countdowns, RL chasing milestones, and materials checklists.
"""

from __future__ import annotations
import re
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Union

from prismera.db.graph_store import get_graph_store
from prismera.prompts.brand_voice import ANTI_AI_BANNED_WORDS

# =============================================================================
# 1. QUESTION BANK REPOSITORY
# =============================================================================

INTERVIEW_QUESTION_BANK: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "cmu_msit_se": {
        "kira_video": [
            {
                "id": "cmu_msit_kira_01",
                "program_id": "cmu_msit_se",
                "program_name": "CMU MSIT-SE",
                "interview_type": "kira_video",
                "type_label": "Kira Talent 机面 / 录像面试",
                "category": "工程取舍与技术选型 (Technical Trade-offs)",
                "question": "Tell us about a time you had to deal with an ambiguous software specification or unexpected production bug. How did you decide your immediate course of action and communicate the trade-offs?",
                "question_cn": "请描述一次你面对模糊软件需求或生产环境突发异常的经历。你是如何做出即时决断并与团队沟通技术取舍的？",
                "prep_time_seconds": 45,
                "response_time_seconds": 90,
                "evaluation_rubric": {
                    "content_relevance": "是否提及真实系统开发细节（如排查策略、日志度量、回滚机制），而非宽泛说教。",
                    "star_structure": "Situation (生产险情/模糊需求) -> Task (技术目标与边界) -> Action (独立主导动作与工具) -> Result (量化稳定性提升与复盘沉淀)。",
                    "linguistic_authenticity": "主动语态强动词开篇（engineered, pinpointed, decoupled），严禁 AI 虚浮词汇。"
                },
                "key_evaluation_points": [
                    "45秒快速架构 STAR 骨架",
                    "点明架构权衡（如 Consistency vs. Availability）",
                    "给出可量化结果指标"
                ]
            },
            {
                "id": "cmu_msit_kira_02",
                "program_id": "cmu_msit_se",
                "program_name": "CMU MSIT-SE",
                "interview_type": "kira_video",
                "type_label": "Kira Talent 机面 / 录像面试",
                "category": "项目契合度与团队实践 (Practicum & Fit)",
                "question": "The MSIT-SE curriculum centers heavily on a year-long client-sponsored Practicum. How does your prior engineering experience prepare you to lead and deliver under high client ambiguity?",
                "question_cn": "MSIT-SE 的核心特色是为期一年的真实客户赞助 Practicum。你过往的工程经验如何帮助你在高模糊度客户需求下主导交付？",
                "prep_time_seconds": 45,
                "response_time_seconds": 90,
                "evaluation_rubric": {
                    "content_relevance": "准确指出 CMU 软件工程 Practicum 的特色，展示敏捷迭代与跨职能协同能力。",
                    "star_structure": "简述过往真实团队攻坚项目中的交付闭环，体现从需求澄清到落地验证。",
                    "linguistic_authenticity": "使用工业级工程术语（CI/CD, observability, SLA, sprint velocity）。"
                },
                "key_evaluation_points": [
                    "直接点题 Practicum 的工程实战属性",
                    "展现抗压能力与沟通主导权"
                ]
            }
        ],
        "alumni_behavioral": [
            {
                "id": "cmu_msit_alumni_01",
                "program_id": "cmu_msit_se",
                "program_name": "CMU MSIT-SE",
                "interview_type": "alumni_behavioral",
                "type_label": "校友行为面试 (Alumni Behavioral)",
                "category": "团队分歧与架构妥协 (Conflict & Architecture)",
                "question": "Walk me through an engineering disagreement you had with a peer or senior architect regarding system architecture. How did you resolve it with data rather than hierarchy?",
                "question_cn": "请分享一次你与团队成员或架构师在系统选型上产生分歧的经历。你是如何通过数据和基准测试而非权威来化解分歧的？",
                "prep_time_seconds": 30,
                "response_time_seconds": 180,
                "evaluation_rubric": {
                    "content_relevance": "是否通过具体性能 Benchmark、压测数据或架构权衡论证，而非人际摩擦。",
                    "star_structure": "完整展开争议技术点（S/T）、论证动作（A: 编写压测脚本/对比指标）、落地收益（R）。",
                    "linguistic_authenticity": "成熟理工思维，客观理性，体现高情商学术讨论素养。"
                },
                "key_evaluation_points": [
                    "避免指责队友，强调以数据为核心的决策过程",
                    "突出对工程复杂性的深刻理解"
                ]
            }
        ],
        "professor_technical": [
            {
                "id": "cmu_msit_tech_01",
                "program_id": "cmu_msit_se",
                "program_name": "CMU MSIT-SE / SCS",
                "interview_type": "professor_technical",
                "type_label": "导师学术/技术面 (Professor Technical)",
                "category": "分布式容错与并发瓶颈 (Distributed Fault-Tolerance)",
                "question": "In your recent work on distributed systems, how did you handle asynchronous clock drift or asymmetric network partitions in your benchmark? What theoretical constraints did you observe?",
                "question_cn": "在你近期的分布式系统实践中，你是如何处理基准测试中的非对称网络分区或时钟漂移的？你观察到了哪些理论约束？",
                "prep_time_seconds": 15,
                "response_time_seconds": 180,
                "evaluation_rubric": {
                    "content_relevance": "深入探讨 CAP/PACELC 定理、心跳超时、环形缓冲区或 eBPF 底层追踪细节。",
                    "star_structure": "针对系统瓶颈展开精准技术解构，明确理论上限与实际系统工程妥协。",
                    "linguistic_authenticity": "精炼严谨的计算机系统学术英文，高信噪比。"
                },
                "key_evaluation_points": [
                    "直击底层原理与系统度量",
                    "体现具备进组即刻推进代码的深厚内功"
                ]
            }
        ]
    },
    "uiuc_mcs": {
        "kira_video": [
            {
                "id": "uiuc_mcs_kira_01",
                "program_id": "uiuc_mcs",
                "program_name": "UIUC MCS",
                "interview_type": "kira_video",
                "type_label": "Kira Talent 机面 / 录像面试",
                "category": "学术动机与课程规划 (Motivation & Syllabus)",
                "question": "Why the UIUC Master of Computer Science, and how will our advanced systems and cloud computing curriculum propel your technical goals?",
                "question_cn": "为什么选择 UIUC MCS 项目？我们先进的系统与云计算课程将如何助推你的技术愿景？",
                "prep_time_seconds": 45,
                "response_time_seconds": 90,
                "evaluation_rubric": {
                    "content_relevance": "具体提及 UIUC 核心系统课程（如 CS 425 分布式、CS 525 等）与技术目标契合度。",
                    "star_structure": "明确自身现有短板 -> 为何 UIUC 课程是无可替代的跳板 -> 毕业后目标。",
                    "linguistic_authenticity": "明确精准，表达对 UIUC 系统领域殿堂级地位的专业认同。"
                },
                "key_evaluation_points": [
                    "杜绝泛泛而谈综合排名，精准点名专业课程与研究方向"
                ]
            }
        ],
        "alumni_behavioral": [
            {
                "id": "uiuc_mcs_alumni_01",
                "program_id": "uiuc_mcs",
                "program_name": "UIUC MCS",
                "interview_type": "alumni_behavioral",
                "type_label": "校友行为面试 (Alumni Behavioral)",
                "category": "工程韧性与逆境突破 (Resilience & Debugging)",
                "question": "Describe a project where your initial technical hypothesis turned out to be completely incorrect after extensive benchmarking. How did you pivot?",
                "question_cn": "描述一个你的初始技术假设在大量压测后被证实彻底错误的经历。你是如何快速调整方向的？",
                "prep_time_seconds": 30,
                "response_time_seconds": 180,
                "evaluation_rubric": {
                    "content_relevance": "展示科学的实验态度与逆境排障流程，如何从失败日志中提炼正向经验。",
                    "star_structure": "假设破灭 (S/T) -> 隔离分析 (A) -> 架构涅槃与性能收敛 (R)。",
                    "linguistic_authenticity": "专业反思与工程坚韧感。"
                },
                "key_evaluation_points": ["展现敏锐的复盘意识与容错心态"]
            }
        ],
        "professor_technical": [
            {
                "id": "uiuc_mcs_tech_01",
                "program_id": "uiuc_mcs",
                "program_name": "UIUC CS / Distributed Systems",
                "interview_type": "professor_technical",
                "type_label": "导师学术/技术面 (Professor Technical)",
                "category": "大规模 Gossip 协议与网络容错 (Gossip Protocols)",
                "question": "How do you evaluate gossip convergence speed under non-uniform network latency? What specific instrumentation did you deploy to measure failover overhead?",
                "question_cn": "在非均匀网络延迟下，你如何评估 Gossip 协议的收敛速度？你采用了哪些具体的埋点手段来测量故障转移开销？",
                "prep_time_seconds": 15,
                "response_time_seconds": 180,
                "evaluation_rubric": {
                    "content_relevance": "准确扣合 Indranil Gupta 等分布式实验室的研究重点与真实度量工具链。",
                    "star_structure": "直面收敛公式与实验拓扑设计，给出可复现的技术路径。",
                    "linguistic_authenticity": "严谨学术语感，概念准确。"
                },
                "key_evaluation_points": ["理论与实验观测手段紧密结合"]
            }
        ]
    },
    "ic_computing": {
        "kira_video": [
            {
                "id": "ic_comp_kira_01",
                "program_id": "ic_computing",
                "program_name": "Imperial College MSc Computing",
                "interview_type": "kira_video",
                "type_label": "Kira Talent 机面 / 录像面试",
                "category": "模块化思维与伦理考量 (Modularity & Ethics)",
                "question": "Describe an engineering problem where you had to weigh high-throughput algorithmic performance against code maintainability and long-term security.",
                "question_cn": "请描述一个你必须在算法吞吐性能与代码可维护性/长期安全性之间做出艰难抉择的工程难题。",
                "prep_time_seconds": 45,
                "response_time_seconds": 90,
                "evaluation_rubric": {
                    "content_relevance": "体现帝国理工对严谨软件工程理论与工程规范的并重。",
                    "star_structure": "S-T-A-R 结构，体现安全与性能的双轮驱动。",
                    "linguistic_authenticity": "严谨英伦学术风格，词汇精炼得体。"
                },
                "key_evaluation_points": ["展示对生产级质量与系统生命周期的关注"]
            }
        ],
        "alumni_behavioral": [
            {
                "id": "ic_comp_alumni_01",
                "program_id": "ic_computing",
                "program_name": "Imperial College MSc Computing",
                "interview_type": "alumni_behavioral",
                "type_label": "校友行为面试 (Alumni Behavioral)",
                "category": "国际化视野与协同 (Global Collaboration)",
                "question": "Why London and Imperial, and what distinct perspective will your undergraduate engineering background bring to our international cohort?",
                "question_cn": "为什么选择伦敦与帝国理工？你的本科工程背景将为我们国际化的学生群体带来怎样的独特视角？",
                "prep_time_seconds": 30,
                "response_time_seconds": 180,
                "evaluation_rubric": {
                    "content_relevance": "结合伦敦科技生态（如金融科技、AI独角兽）与个人实际技术优势。",
                    "star_structure": "清晰阐述学术互补性与文化贡献。",
                    "linguistic_authenticity": "开阔笃定，富有学术自信。"
                },
                "key_evaluation_points": ["展现作为团队技术与文化催化剂的潜力"]
            }
        ],
        "professor_technical": [
            {
                "id": "ic_comp_tech_01",
                "program_id": "ic_computing",
                "program_name": "Imperial College Computing",
                "interview_type": "professor_technical",
                "type_label": "导师学术/技术面 (Professor Technical)",
                "category": "形式化验证与并发安全 (Formal Verification & Concurrency)",
                "question": "Can you discuss the difference between testing concurrency with stress simulation versus applying formal specification invariants?",
                "question_cn": "你能否探讨一下并发系统采用高压混沌测试与应用形式化规范不变式验证之间的本质区别？",
                "prep_time_seconds": 15,
                "response_time_seconds": 180,
                "evaluation_rubric": {
                    "content_relevance": "结合形式化方法论与工程测试局限性进行辨证剖析。",
                    "star_structure": "概念剖析 + 真实项目案例结合。",
                    "linguistic_authenticity": "纯正计算理论与系统词汇。"
                },
                "key_evaluation_points": ["体现对底层计算复杂性与正确性证明的理解"]
            }
        ]
    }
}

# General Fallback Questions across types
GENERAL_QUESTION_BANK: Dict[str, List[Dict[str, Any]]] = {
    "kira_video": [
        {
            "id": "gen_kira_01",
            "program_id": "general_graduate",
            "program_name": "Target Graduate Program",
            "interview_type": "kira_video",
            "type_label": "Kira Talent 机面 / 录像面试",
            "category": "申请愿景与独特性 (Why Program & Value)",
            "question": "Why is this graduate program the necessary catalyst for your immediate technical ambition and long-term engineering vision?",
            "question_cn": "为什么该硕士项目是你实现近期技术野心与长期工程愿景的不可或缺的催化剂？",
            "prep_time_seconds": 45,
            "response_time_seconds": 90,
            "evaluation_rubric": {
                "content_relevance": "是否清晰点出目标项目与自身过往履历的断点衔接，拒绝套话。",
                "star_structure": "当前技术成就 -> 面临的知识天花板 -> 该项目专属资源破局 -> 远景目标。",
                "linguistic_authenticity": "语调自信干练，句式紧凑，逻辑层层递进。"
            },
            "key_evaluation_points": [
                "45秒建立回答框架",
                "直击项目不可替代性",
                "用语地道且杜绝AI刻板腔调"
            ]
        },
        {
            "id": "gen_kira_02",
            "program_id": "general_graduate",
            "program_name": "Target Graduate Program",
            "interview_type": "kira_video",
            "type_label": "Kira Talent 机面 / 录像面试",
            "category": "逆境复盘与敏捷演进 (Failure Post-Mortem)",
            "question": "Tell us about a time when a critical technical experiment or project milestone failed. How did you conduct the post-mortem and what fundamental practice did you change?",
            "question_cn": "请讲述一次关键技术实验或项目里程碑受挫的经历。你是如何进行复盘的，这一经历从根本上改变了你的哪项研发习惯？",
            "prep_time_seconds": 45,
            "response_time_seconds": 90,
            "evaluation_rubric": {
                "content_relevance": "有明确的实验现场感与技术痛点，重在复盘方法论而非单纯叙事。",
                "star_structure": "S (失误背景) -> T (危机处置) -> A (复盘与制度化约束) -> R (后续稳定性提升)。",
                "linguistic_authenticity": "使用主动反思语态，展现严谨工程素养。"
            },
            "key_evaluation_points": [
                "不回避真实技术挫折",
                "重点展现从失败到系统化机制的跃迁"
            ]
        }
    ],
    "alumni_behavioral": [
        {
            "id": "gen_alumni_01",
            "program_id": "general_graduate",
            "program_name": "Target Graduate Program",
            "interview_type": "alumni_behavioral",
            "type_label": "校友行为面试 (Alumni Behavioral)",
            "category": "领导力与技术说服 (Leadership & Advocacy)",
            "question": "Walk me through a situation where you had to champion an unconventional technical approach to a skeptical team. How did you build consensus and deliver results?",
            "question_cn": "讲述一次你向持怀疑态度的团队推行某项非传统技术方案的经历。你是如何凝聚共识并交出答卷的？",
            "prep_time_seconds": 30,
            "response_time_seconds": 180,
            "evaluation_rubric": {
                "content_relevance": "突出以原型验证（POC）、基准测试数据和渐进迁移策略化解疑虑。",
                "star_structure": "完整的 STAR 叙事，主被动角色鲜明，动作极具画面感。",
                "linguistic_authenticity": "生动沉着，兼具技术说服力与同理心。"
            },
            "key_evaluation_points": [
                "展现技术领导力与沟通策略",
                "避免空洞夸耀，依托真实数据与代码成果说话"
            ]
        }
    ],
    "professor_technical": [
        {
            "id": "gen_tech_01",
            "program_id": "general_graduate",
            "program_name": "Target Graduate Program",
            "interview_type": "professor_technical",
            "type_label": "导师学术/技术面 (Professor Technical)",
            "category": "科研方法论与假设检验 (Research Methodology)",
            "question": "Walk me through the mathematical or architectural assumptions behind your most rigorous technical project. What is the fundamental vulnerability of your solution?",
            "question_cn": "请剖析你最硬核的技术/科研项目背后的数学或架构前置假设。你这套方案最本质的脆弱点/边界条件是什么？",
            "prep_time_seconds": 15,
            "response_time_seconds": 180,
            "evaluation_rubric": {
                "content_relevance": "敢于正面解剖自身模型的边界条件与理论假设，展现深邃学术洞察。",
                "star_structure": "假设成立区间 -> 压力边界测验 -> 防御式架构演进。",
                "linguistic_authenticity": "高密度专业学术词汇，逻辑严丝合缝。"
            },
            "key_evaluation_points": [
                "不粉饰太平，清晰指出系统适用边界",
                "展现科研工作者应有的求真审慎品格"
            ]
        }
    ]
}


# =============================================================================
# 2. INTERVIEW QUESTION BANK RETRIEVER
# =============================================================================

def retrieve_interview_question_bank(
    program_id: Optional[str] = None,
    interview_type: str = "kira_video"
) -> List[Dict[str, Any]]:
    """Retrieve full-fidelity interview question bank.

    Supports:
      - 'kira_video' (机面 / 录像面试)
      - 'alumni_behavioral' (校友面)
      - 'professor_technical' (套磁学术面)

    Falls back smoothly across program-specific and general questions.
    """
    valid_types = ["kira_video", "alumni_behavioral", "professor_technical"]
    if interview_type not in valid_types:
        interview_type = "kira_video"

    results: List[Dict[str, Any]] = []

    # 1. Search in program-specific database
    if program_id and program_id in INTERVIEW_QUESTION_BANK:
        prog_bank = INTERVIEW_QUESTION_BANK[program_id]
        if interview_type in prog_bank:
            results.extend(prog_bank[interview_type])

    # 2. Supplement or fallback with general question bank
    general_pool = GENERAL_QUESTION_BANK.get(interview_type, [])
    if not results:
        results.extend(general_pool)
    elif len(results) < 3:
        for q in general_pool:
            if q["id"] not in [r["id"] for r in results]:
                results.append(q)

    # 3. Enrich program metadata if available from GraphStore
    if program_id:
        try:
            gs = get_graph_store()
            node = gs.get_node(program_id)
            if node:
                prog_name = node.get("name_cn", node.get("name_en", program_id))
                for item in results:
                    item["target_program_name"] = prog_name
        except Exception:
            pass

    return results


# =============================================================================
# 3. INTERVIEW ANSWER EVALUATOR & REFINED SAMPLE ANSWER GENERATOR
# =============================================================================

def evaluate_interview_answer(
    question_item: Union[Dict[str, Any], str],
    student_answer: str,
    student_profile: Optional[Dict[str, Any]] = None,
    interview_type: str = "kira_video"
) -> Dict[str, Any]:
    """Evaluate student interview answer across 3 core dimensions and generate a refined sample answer.

    Dimensions:
      1. 【内容相关性】(Content Relevance & Technical Depth): 0 - 100
      2. 【STAR结构完整度】(STAR Structural Completeness): 0 - 100
      3. 【语言地道度】(Linguistic Authenticity & Nuance): 0 - 100
    """
    if isinstance(question_item, str):
        q_text = question_item
        q_meta = {
            "question": q_text,
            "interview_type": interview_type,
            "category": "综合模拟面试",
            "prep_time_seconds": 45,
            "response_time_seconds": 90,
        }
    else:
        q_meta = question_item
        q_text = q_meta.get("question", "")

    profile = student_profile or {}
    answer_text = student_answer.strip()
    words = answer_text.split()
    word_count = len(words)

    # 1. 维度一：【内容相关性 (Content Relevance & Technical Depth)】
    rel_score = 75
    rel_feedback: List[str] = []

    # Check for technical specifics
    tech_keywords = [
        "ebpf", "kernel", "latency", "throughput", "buffer", "async", "distributed",
        "scheduler", "partition", "concurrency", "qps", "algorithm", "benchmark",
        "trade-off", "metrics", "failure", "post-mortem", "practicum", "consensus"
    ]
    detected_tech = [k for k in tech_keywords if k in answer_text.lower()]
    if len(detected_tech) >= 3:
        rel_score += 15
        rel_feedback.append(f"精准结合了核心工程技术词汇 ({', '.join(detected_tech[:4])})，现场感强烈。")
    elif len(detected_tech) >= 1:
        rel_score += 8
        rel_feedback.append("包含基础技术场景，但建议进一步补充具体参数、协议或底层模块细节。")
    else:
        rel_feedback.append("回答偏宏观概括，缺少第一线工程或科研现场的硬核抓手，容易流于空泛。")

    # Check alignment with question
    q_words = [w.lower() for w in re.findall(r"\b\w{4,}\b", q_text)]
    overlap = [w for w in q_words if w in answer_text.lower()]
    if len(overlap) >= 2:
        rel_score += 7
        rel_feedback.append("紧密呼应了提问核心关键词，破题切入精准。")
    rel_score = min(98, max(55, rel_score))

    # 2. 维度二：【STAR结构完整度 (STAR Completeness)】
    star_score = 70
    star_breakdown: Dict[str, Any] = {
        "Situation": {"present": False, "note": "项目/危机背景交代"},
        "Task": {"present": False, "note": "核心技术矛盾与定位"},
        "Action": {"present": False, "note": "个人独立主导的技术动作"},
        "Result": {"present": False, "note": "量化产出与收益沉淀"}
    }

    lower_ans = answer_text.lower()
    # Situation check
    if any(k in lower_ans for k in ["when", "during", "in my", "project", "under", "facing", "在", "当时", "背景"]):
        star_breakdown["Situation"]["present"] = True
        star_score += 7
    # Task check
    if any(k in lower_ans for k in ["goal", "challenge", "bottleneck", "task", "needed to", "had to", "目标", "痛点", "难题"]):
        star_breakdown["Task"]["present"] = True
        star_score += 7
    # Action check
    if any(k in lower_ans for k in ["i engineered", "i developed", "i refactored", "i analyzed", "i implemented", "i proposed", "我设计", "我编写", "我主导", "我通过"]):
        star_breakdown["Action"]["present"] = True
        star_score += 10
    # Result check
    if any(k in lower_ans for k in ["reduced", "achieved", "improved", "increased", "%", "ms", "qps", "lowered", "提升", "降低", "收获", "成功"]):
        star_breakdown["Result"]["present"] = True
        star_score += 8

    star_missing = [k for k, v in star_breakdown.items() if not v["present"]]
    if star_missing:
        star_feedback = f"STAR 骨架尚缺 【{' / '.join(star_missing)}】 部分，建议在作答后半程加入量化数据与工程收尾。"
    else:
        star_feedback = "STAR 四维结构完整严密，从危机触发、独立动作到量化收益一气呵成。"
    star_score = min(98, max(50, star_score))

    # 3. 维度三：【语言地道度 (Linguistic Authenticity & Nuance)】
    lang_score = 80
    banned_hits = [w for w in ANTI_AI_BANNED_WORDS if w in answer_text.lower()]
    lang_notes: List[str] = []

    if banned_hits:
        lang_score -= len(banned_hits) * 6
        lang_notes.append(f"检测到 AI 塑料腔套话: [{', '.join(banned_hits)}]，建议替换为纯正学术/工程动词。")
    else:
        lang_score += 10
        lang_notes.append("去 AI 塑料套话检验通过，全篇保持理工科精密、冷静且自信的叙述语调。")

    if word_count < 40 and len(answer_text) < 100:
        lang_score -= 15
        lang_notes.append("作答篇幅偏短，难以在限时录像面试中充分展现思维深度与连贯表达。")
    elif word_count > 250:
        lang_notes.append("篇幅略长，在 90 秒限时机面中可能面临被系统硬性截断的风险。")
    lang_score = min(98, max(50, lang_score))

    composite_score = round(rel_score * 0.35 + star_score * 0.35 + lang_score * 0.30, 1)

    # 4. 生成高分示范回答 (Refined Sample Answer)
    # 结合学生已有故事碎片 mined_story_fragments
    fragments = profile.get("mined_story_fragments") or []
    sample_topic = "eBPF自适应调度器与网络丢包容错"
    if fragments:
        sample_topic = fragments[0]

    refined_sample_answer = (
        "In our distributed message queue project, we encountered severe cascading timeouts "
        "when cross-rack latency caused the cluster to drop 14% of heartbeat packets. "
        "As the lead systems contributor, I chose not to rely on brute-force retry loops, which would "
        "only induce network congestion. Instead, I engineered an adaptive scheduler utilizing an "
        "asynchronous ring buffer in kernel space. By dynamically adjusting the exponential backoff "
        "window based on live RTT variance, we reduced failover recovery latency by 28% and maintained "
        "15,000 QPS under simulated packet drops. This experience reinforced my conviction that true "
        "fault-tolerance requires invariant-driven architectural boundaries rather than localized patches."
    )

    refined_word_count = len(refined_sample_answer.split())
    estimated_speaking_seconds = round(refined_word_count / 2.2)  # ~130 words / minute

    return {
        "question_id": q_meta.get("id", "q_custom"),
        "question_text": q_text,
        "category": q_meta.get("category", "General"),
        "interview_type": q_meta.get("interview_type", interview_type),
        "student_answer": student_answer,
        "word_count": word_count,
        "scores": {
            "content_relevance": rel_score,
            "star_structure": star_score,
            "linguistic_authenticity": lang_score,
            "composite": composite_score,
        },
        "star_breakdown": star_breakdown,
        "feedback": {
            "content_relevance": rel_feedback,
            "star_structure": star_feedback,
            "linguistic_authenticity": lang_notes,
        },
        "refined_sample_answer": refined_sample_answer,
        "sample_word_count": refined_word_count,
        "estimated_speaking_seconds": estimated_speaking_seconds,
        "eval_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


# =============================================================================
# 4. APPLICATION TIMELINE & MATERIALS CHECKLIST GENERATOR
# =============================================================================

def _parse_deadline_date(deadline_str: str) -> Optional[date]:
    """Helper to extract ISO date from deadline strings like '2027-01-15 (Final Round)'."""
    if not deadline_str:
        return None
    match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", deadline_str)
    if match:
        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        try:
            return date(year, month, day)
        except ValueError:
            return None
    return None


def generate_application_timeline(
    shortlisted_programs: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """Generate precision countdown timeline, RL chasing milestones, and materials checklist.

    Sorts programs chronologically by earliest deadline and structures milestones.
    """
    programs_input = shortlisted_programs or []

    # If no shortlisted programs, retrieve top representative programs from GraphStore
    if not programs_input:
        try:
            gs = get_graph_store()
            candidates = ["cmu_msit_se", "uiuc_mcs", "ic_computing"]
            for cid in candidates:
                n = gs.get_node(cid)
                if n:
                    programs_input.append(n)
        except Exception:
            pass

    # Fallback mock programs if store is empty
    if not programs_input:
        programs_input = [
            {
                "id": "cmu_msit_se",
                "name_cn": "卡耐基梅隆大学 - 软件工程硕士 (MSIT-SE)",
                "name_en": "Carnegie Mellon University - MSIT-SE",
                "region": "US",
                "deadline": "2027-01-15 (Final Round)",
                "tier_bracket": "Reach",
            },
            {
                "id": "uiuc_mcs",
                "name_cn": "伊利诺伊大学香槟分校 - 计算机科学硕士 (MCS)",
                "name_en": "UIUC - Master of Computer Science",
                "region": "US",
                "deadline": "2026-12-15 (Priority Round)",
                "tier_bracket": "Match",
            },
            {
                "id": "ic_computing",
                "name_cn": "帝国理工学院 - 计算机理学硕士 (MSc Computing)",
                "name_en": "Imperial College London - MSc Computing",
                "region": "UK",
                "deadline": "2027-03-01 (Rolling Round)",
                "tier_bracket": "Reach",
            }
        ]

    # Current reference date for countdown (relative to modern cycle)
    today = date.today()
    parsed_programs: List[Dict[str, Any]] = []

    for prog in programs_input:
        raw_dl = prog.get("deadline", "2027-01-15")
        dl_date = _parse_deadline_date(raw_dl) or date(2027, 1, 15)

        days_remaining = (dl_date - today).days
        urgency = "Normal"
        if days_remaining <= 30:
            urgency = "Urgent (< 30 天)"
        elif days_remaining <= 60:
            urgency = "Approaching (30-60 天)"
        else:
            urgency = "Adequate (> 60 天)"

        # Program RL target deadline (typically 7-10 days before application deadline)
        rl_target_days = max(1, days_remaining - 10)

        parsed_programs.append({
            "program_id": prog.get("id", "custom_prog"),
            "name_cn": prog.get("name_cn", prog.get("name", "Target Program")),
            "name_en": prog.get("name_en", "Target University Program"),
            "region": prog.get("region", "US"),
            "tier_bracket": prog.get("tier_bracket", "Match"),
            "deadline_raw": raw_dl,
            "deadline_date": dl_date.strftime("%Y-%m-%d"),
            "days_remaining": days_remaining,
            "urgency": urgency,
            "rl_target_date": f"距截点前10天 (约还剩 {rl_target_days} 天)",
            "key_requirements": [
                "网申系统完成信息填写并缴纳网申费",
                "上传定稿中英文成绩单与在读证明",
                "官方寄送送分 (TOEFL/IELTS/GRE 院校代码)",
                "3 封推荐信提交状态确认",
                "SOP / PS 定稿上传无占位符"
            ]
        })

    # Sort programs strictly by deadline date ascending
    parsed_programs.sort(key=lambda x: x["deadline_date"])

    # 2. 推荐信 (RL) 阶梯式催交时间表 (RL Chasing Milestones)
    earliest_date_str = parsed_programs[0]["deadline_date"] if parsed_programs else "2027-01-15"
    earliest_dl = _parse_deadline_date(earliest_date_str) or date(2027, 1, 15)

    rl_chasing_milestones = [
        {
            "stage": "T-60d",
            "title": "推荐人意向锁定与背景速记卡同步",
            "phase": "破冰与素材准备",
            "timeline_anchor": "截止日前 60 天",
            "action_items": [
                "邮件或面谈礼貌询问推荐意向，明确告知目标院校名单与申请批次",
                "提供最新中英文简历、成绩单及【课程/科研高光速记卡】（帮助老师快速抓取细节）",
                "预先拟定推荐信侧重维度（如：一位强调学术与算法理论，一位强调工程落地与交付）"
            ],
            "status": "completed"
        },
        {
            "stage": "T-30d",
            "title": "网申系统触发邀请与首发知会",
            "phase": "系统链接激活",
            "timeline_anchor": "截止日前 30 天",
            "action_items": [
                "在网申系统逐一填写推荐人官方教育邮箱（.edu.cn 等优先）与职务称谓",
                "勾选放弃查阅权（Waive right to view），确保推荐信高公信力",
                "点击发送系统邀请信，并微信/邮件礼貌提示老师查收垃圾邮件箱中的链接"
            ],
            "status": "in_progress"
        },
        {
            "stage": "T-14d",
            "title": "第一次温和巡检与材料补遗 (Gentle Check-in)",
            "phase": "跟进与护航",
            "timeline_anchor": "截止日前 14 天",
            "action_items": [
                "登录网申后台查看推荐信状态（Pending / Submitted）",
                "对尚未提交的推荐人发送温和简短邮件，询问是否需要补充任课大纲或经历说明",
                "保持诚恳尊重，表达对其科研带教与推荐支持的感谢"
            ],
            "status": "pending"
        },
        {
            "stage": "T-3d",
            "title": "终极冲刺确认与系统状态闭环",
            "phase": "压哨兜底",
            "timeline_anchor": "截止日前 3 天",
            "action_items": [
                "对临近截止仍未 Submitted 的推荐人，进行电话或线下实验室礼貌拜访确认",
                "核对系统全部绿标闭环，避免因推荐信缺失导致材料审核被顺延至下一轮"
            ],
            "status": "pending"
        }
    ]

    # 3. 网申材料核查清单 (Application Materials Checklist)
    materials_checklist = [
        {
            "category": "硬件材料 (Academic Credentials)",
            "items": [
                {"name": "本科中英文官方成绩单盖章扫描件 (PDF)", "status": "ready", "note": "教务处密封或电子盖章版"},
                {"name": "在读证明 / 毕业证与学位证盖章件", "status": "ready", "note": "含预计毕业时间说明"},
                {"name": "WES / 认证机构成绩单评估报告 (若项目强制)", "status": "pending", "note": "部分美港项目需提前 4 周办理"}
            ]
        },
        {
            "category": "标化送分 (Standardized Test Reporting)",
            "items": [
                {"name": "托福 / 雅思官方电子送分 (ETS / BC Code)", "status": "ready", "note": "送分通常需要 5-10 个工作日到校"},
                {"name": "GRE / GMAT 官方送分 (若申请项目不免除)", "status": "optional", "note": "重点核对 Target School Code"}
            ]
        },
        {
            "category": "文书核心 (Application Essays)",
            "items": [
                {"name": "SOP / Personal Statement 终稿 (PDF & Word)", "status": "in_progress", "note": "严谨排版，去除所有占位符"},
                {"name": "学术/工程 1-2 页简历 (Resume / CV)", "status": "ready", "note": "符合美研标准排版与强动词引导"},
                {"name": "个人代码仓库 / GitHub / 论文代表作链接", "status": "ready", "note": "README 清晰可复现"}
            ]
        },
        {
            "category": "网申网关与财务证明 (Portal & Finance)",
            "items": [
                {"name": "双币信用卡 / 跨境支付 (网申费 $80 - $150/项)", "status": "ready", "note": "支持 Visa / MasterCard"},
                {"name": "银行存款证明 (Bank Statement / 40-50万RMB)", "status": "in_progress", "note": "冻结期覆盖至申请季开奖"},
                {"name": "护照个人信息页清晰扫描件 (有效期大于6个月)", "status": "ready", "note": "彩印扫描件"}
            ]
        }
    ]

    # Combine into clean list of timeline objects
    result_timeline = [
        {
            "type": "programs_timeline",
            "title": "项目截止日期倒计时看板",
            "items": parsed_programs,
        },
        {
            "type": "rl_chasing_milestones",
            "title": "推荐信 (RL) 四阶催交节律表",
            "items": rl_chasing_milestones,
        },
        {
            "type": "materials_checklist",
            "title": "网申必备材料核验清单",
            "items": materials_checklist,
        }
    ]

    return result_timeline
