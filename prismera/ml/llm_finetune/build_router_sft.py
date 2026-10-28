"""Builder for Prism-Luminary Router SFT (Supervised Fine-Tuning) Dataset.

Constructs instruction fine-tuning datasets formatted for LLaMA-Factory and TRL
SFTTrainer to train lightweight 1.5B/3B edge router models:
  {"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]}

Every generated assistant message is strictly validated against the Pydantic
`LuminaryDecision` schema.
"""

from __future__ import annotations
import argparse
import json
import os
import random
from pathlib import Path
from typing import Dict, Any, List

from prismera.state import LuminaryDecision
from prismera.prompts.luminary import LUMINARY_SYSTEM_PROMPT

ROUTING_SCENARIOS = [
    # 1. prism_facet (Background Parsing & Ingestion)
    {
        "category": "facet_intake",
        "user_queries": [
            "这是我的本科成绩单文本：浙大计算机专业，大一到大三GPA 3.84/4.0，雅思7.5（听力8.0 阅读8.0 写作7.0 口语6.5），请帮我解析建档。",
            "我刚上传了我的简历PDF文本。主要经历包括一段微软后端实习、一段国家重点实验室科研，GPA大约是88/100，双非一本软件工程。请帮我录入档案并梳理切面画像。",
            "我是华科软件工程的本科生，均分87.2，托福105，目前有一篇二作论文在投。请先帮我建立学生基本切面档案。",
            "麻烦帮我录入下背景：复旦大学微电子专业，GPA 3.65/4.0，想要跨考申请美国的CS/ECE硕士，目前雅思总分7.0，小分6.5。",
            "我刚整理好了我的大学成绩单：211北京邮电大学计算机，加权平均分89.4分，已考GRE 328+3.5，语言雅思7.5。请帮我拆解背景切面。",
        ],
        "state_template": {
            "undergrad_tier": "{tier}",
            "undergrad_name": "{school}",
            "gpa_raw": "{gpa}",
            "major": "{major}",
            "language_scores": {"IELTS_total": 7.5, "speaking": 6.5},
        },
        "target_agent": "prism_facet",
        "thought": "用户提供了详细的本科院校、专业背景、GPA以及语言标化成绩，需要先由切面师 (prism_facet) 完成信息结构化建档并生成学生光谱画像。",
        "briefing": "解析用户提供的学术背景与标化数据，补齐 StudentSpectrumProfile 各核心字段，完成结构化切面沉淀。",
        "decision": "DELEGATE_TO_AGENT",
    },
    # 2. prism_locus (School Selection Matrix & Admission Predictor)
    {
        "category": "locus_matrix",
        "user_queries": [
            "我的档案已经建好了（985计科，GPA 3.82，雅思7.5）。请帮我推荐英国和美国的选校名单，需要冲刺、核心和保底三档方案。",
            "根据我的背景，CMU的MSIT-SE或者帝国理工的Computing硕士，录取概率大概是多少？请结合往年同辈案例给出选校建议。",
            "我想申请新加坡和中国香港的CS/DS硕士（目前NUS、NTU、HKU）。请帮我做一下知识图谱硬核剪枝和定焦矩阵排查。",
            "请结合我的条件给我一份选校方案：我想主要考虑美国和英国支持3年OPT的STEM硕士项目，预算大约在60万人民币以内。",
            "基于我目前双非一本、GPA 3.9、托福108的背景，能申请到哪些美国Top 30的CS项目？请定焦师运行同辈案例校准。",
        ],
        "state_template": {
            "target_regions": ["US", "UK", "SG", "HK"],
            "target_majors": ["CS", "DS"],
        },
        "target_agent": "prism_locus",
        "thought": "用户核心诉求是定位目标项目与选校定档。申请者基础背景已具备，应调度定焦师 (prism_locus) 执行知识图谱剪枝与 AdmitNet 机器学习概率归因排查。",
        "briefing": "执行 GraphRAG 三步定焦法与 Prism-AdmitNet 概率预测，产出冲稳保三维光谱选校矩阵并标注特征归因。",
        "decision": "DELEGATE_TO_AGENT",
    },
    # 3. prism_disperser (Essay Crafting & Anti-AI Refraction)
    {
        "category": "disperser_essay",
        "user_queries": [
            "我正在写CMU MSIT-SE项目的个人陈述（PS），想把我在分布式KV存储系统里解决多线程RPC锁争用的经历写进去，请帮我起草核心段落，拒绝AI陈词滥调！",
            "帮我润色这段文书草稿：'My unwavering passion has driven me to delve into the rich tapestry of deep learning...'，请用 Show-Don't-Tell 风格彻底去AI化！",
            "这是我针对帝国理工Computing项目的文书动机段，希望能具体结合Prof. Francesca Toni的研究方向和COMP70015深度学习课程进行精准折射。",
            "请帮我用苏格拉底提问法梳理一下我的科研项目故事线，我有一篇低资源NLP论文，不知道如何在PS里凸显我的独立贡献。",
            "请针对我的实习经历（字节跳动高并发网关开发）提炼出2条高含金量的英文简历（CV）Bullet Points，要求包含具体量化指标与技术栈。",
        ],
        "state_template": {
            "active_document_type": "PS",
        },
        "target_agent": "prism_disperser",
        "thought": "用户提出了文书创作、局部润色或反AI套话审查的需求。应调度折光师 (prism_disperser) 运用苏格拉底提问与局部折射引擎处理。",
        "briefing": "以棱镜纪 Authentic Human 叙事标准起草/润色文书，严禁使用 delve into 等塑料词汇，突出量化指标与工程因果闭环。",
        "decision": "DELEGATE_TO_AGENT",
    },
    # 4. prism_resonator (Mock Interview & Behavioral Simulation)
    {
        "category": "resonator_interview",
        "user_queries": [
            "我下周有CMU的视频面试（Video Interview），能帮我模拟一场15分钟的技术与行为面试吗？请扮演严苛的技术面试官！",
            "我想针对帝国理工的学术面试做模拟演练，请根据我的分布式系统科研经历向我提出3个刁钻的学术质疑问题。",
            "请扮演一位卡耐基梅隆大学的终身教授，针对我的推荐信和文书里提到的分布式事务一致性算法对我进行模拟追问。",
            "请帮我准备常见留学面试中的'Why This Program'和'Walk me through your CV'两道核心问题的应答策略与模拟演练。",
        ],
        "state_template": {
            "interview_target_program": "cmu_msit_se",
        },
        "target_agent": "prism_resonator",
        "thought": "用户需要进行海外硕士申请的模拟面试演练。应调度共鸣师 (prism_resonator) 加载教授画像仿真引擎进行学术质询模拟。",
        "briefing": "扮演目标项目教授面试官，基于学生背景档案进行多轮严谨且具压迫感的学术面试与即时反馈诊断。",
        "decision": "DELEGATE_TO_AGENT",
    },
    # 5. prism_echo (Letter of Recommendation Persona & Referee Alignment)
    {
        "category": "echo_recommendation",
        "user_queries": [
            "我的科研导师同意帮我提交推荐信，但让我先拟定一份初稿。导师是分布式系统领域的正教授，请帮我生成一封符合教授视角的推荐信（RL）。",
            "我需要准备一封来自微软实习主管的业界推荐信，重点体现我的工程交付能力、代码鲁棒性与团队敏捷协同，请帮我起草。",
            "请帮我规划三封推荐信的差异化策略（班主任侧重GPA学业基底，科研导师侧重创新力，企业Leader侧重业务闭环），避免千篇一律。",
            "我找了一位海外交流期间认识的教授写推荐信，怎样在推荐信里自然融入教授对我的研讨会发言和期末Paper的正面评价？",
        ],
        "state_template": {
            "recommender_type": "academic_advisor",
        },
        "target_agent": "prism_echo",
        "thought": "用户需要规划或起草推荐人视角的推荐信。应调度回声师 (prism_echo) 加载推荐人数字孪生模型进行差异化声纹撰写。",
        "briefing": "以权威学术导师/企业主管的第一人称口吻撰写高信噪比推荐信，侧重具体共事细节，与学生自述文书形成呼应互证。",
        "decision": "DELEGATE_TO_AGENT",
    },
    # 6. ASK_FOR_CLARIFICATION (Insufficient baseline parameters)
    {
        "category": "clarification",
        "user_queries": [
            "帮我看看我能申什么学校？",
            "我想去美国读计算机硕士，有哪些推荐？",
            "你好，我想出国留学，请问该怎么准备？",
            "我想申请明年的秋季入学，求规划。",
        ],
        "state_template": {},
        "target_agent": None,
        "thought": "用户表达了强烈的申请意愿，但尚未提供本科院校梯队、GPA、目标专业或语言成绩等关键基准信息，尚无法触发选校图谱剪枝。需要温和引导用户补全基准四要素。",
        "briefing": None,
        "decision": "ASK_FOR_CLARIFICATION",
        "message_to_user": "每一束原光的精准折射，都需要依托清晰的物理切面。为了为你量身构建选校坐标系，请先告诉我你的：\n1. 本科院校及所在梯队（如：985/211/海本/双非）\n2. 当前加权平均分（GPA）\n3. 拟申请的方向（如：计算机CS / 数据科学DS）\n4. 当前语言成绩（如雅思/托福）或备考计划。\n（你也可以直接发送你的成绩单截图或文本，我将为你一键解析建档。）",
    },
    # 7. DIRECT_ANSWER (System scope, onboarding, general Q&A)
    {
        "category": "direct_answer",
        "user_queries": [
            "你好，请问 PrismEra 棱镜纪是一个什么样的系统？和传统留学中介有什么区别？",
            "你们系统的选校概率是用什么模型预测的？",
            "文书里的 Anti-AI 审查机制具体是怎么工作的？",
            "谢谢司光者，我明白了！",
        ],
        "state_template": {},
        "target_agent": None,
        "thought": "用户询问系统定位、算法机制或礼貌致意，属于司光者全局职责范畴，直接以棱镜纪智性温和的品牌语调给出专业解答。",
        "briefing": None,
        "decision": "DIRECT_ANSWER",
        "message_to_user": "PrismEra（棱镜纪）是一套基于 LangGraph 认知图谱与多智能体协同架构的自主留学折射系统。与传统中介推销话术不同，我们以严谨的全球院校知识图谱（GraphRAG）、自训练机器学习录取率预测模型（Prism-AdmitNet）以及去AI套话的叙事折射师为基石，致力于消除信息黑盒，让每一段沉默履历折射出其独有的学术光谱。",
    },
]

SCHOOL_TIER_SAMPLES = [
    ("清华大学", "985", "3.88/4.0", "计算机科学与技术"),
    ("浙江大学", "985", "3.82/4.0", "软件工程"),
    ("上海交通大学", "985", "3.75/4.0", "电子信息"),
    ("北京邮电大学", "211", "88.5/100", "计算机科学"),
    ("华中科技大学", "985", "87.0/100", "光电信息工程"),
    ("华盛顿大学", "海本", "3.72/4.0", "Computer Science"),
    ("深圳大学", "双非一本", "3.90/4.0", "软件工程"),
    ("南京大学", "985", "3.80/4.0", "人工智能"),
]


def build_router_sft_sample(idx: int) -> Dict[str, Any]:
    """Build a single instruction SFT conversation sample."""
    scenario = ROUTING_SCENARIOS[idx % len(ROUTING_SCENARIOS)]
    user_query = random.choice(scenario["user_queries"])
    school, tier, gpa, major = random.choice(SCHOOL_TIER_SAMPLES)

    # Customize state updates if applicable
    state_updates = dict(scenario["state_template"])
    if "{tier}" in str(state_updates):
        state_updates["undergrad_tier"] = tier
        state_updates["undergrad_name"] = school
        state_updates["gpa_raw"] = gpa
        state_updates["major"] = major

    decision = LuminaryDecision(
        luminary_thought=scenario["thought"],
        state_updates=state_updates,
        routing_decision=scenario["decision"],
        target_agent_id=scenario["target_agent"],
        task_briefing=scenario["briefing"],
        message_to_user=scenario.get("message_to_user"),
    )

    decision_json = decision.model_dump_json(indent=2)

    return {
        "messages": [
            {
                "role": "system",
                "content": LUMINARY_SYSTEM_PROMPT.strip(),
            },
            {
                "role": "user",
                "content": user_query,
            },
            {
                "role": "assistant",
                "content": decision_json,
            },
        ]
    }


def generate_router_sft_dataset(
    output_path: str = "data/finetune/luminary_sft_train.jsonl",
    num_samples: int = 300,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """Synthesize and write Luminary Router SFT dataset to disk."""
    random.seed(seed)
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    samples: List[Dict[str, Any]] = []

    for idx in range(num_samples):
        sample = build_router_sft_sample(idx)
        # Validation: Verify assistant content parses into LuminaryDecision
        assistant_content = sample["messages"][2]["content"]
        LuminaryDecision.model_validate_json(assistant_content)
        samples.append(sample)

    with open(out_file, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    return samples


def main():
    parser = argparse.ArgumentParser(description="PrismEra Luminary Router SFT Dataset Builder")
    parser.add_argument(
        "--output",
        type=str,
        default="data/finetune/luminary_sft_train.jsonl",
        help="Target output JSONL path",
    )
    parser.add_argument(
        "--num_samples",
        type=int,
        default=300,
        help="Number of instruction conversations to synthesize",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    samples = generate_router_sft_dataset(
        output_path=args.output,
        num_samples=args.num_samples,
        seed=args.seed,
    )
    print(f"Successfully generated {len(samples)} Router SFT conversations -> {args.output}")


if __name__ == "__main__":
    main()
