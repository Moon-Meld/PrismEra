# 🔬 PrismEra GraphRAG 自动化量化评测基准报告 (Evaluation Benchmark Report)

> **评测时间**：`2026-10-28T10:23:20.618535+00:00`  
> **评测用例集**：`benchmarks/eval_dataset.json`（涵盖 **28 个** 真实留学申请高危陷阱题）  
> **对比方案**：**Baseline 纯 Prompt 模式** vs **PrismEra GraphRAG 多智能体协同模式**

---

## 1. 核心量化指标对比（Core Quantitative Metrics）

| 核心评测维度 (Evaluation Metric) | Baseline (纯 Prompt 模式) | PrismEra (GraphRAG 多智能体) | 性能提升 (Delta) | 核心壁垒说明 |
| :--- | :---: | :---: | :---: | :--- |
| **`Hard_Constraint_Precision`**<br>(硬性门槛拦截精准率) | **0.0%** | **100.0%** | <span style="color:green;font-weight:bold;">+100.0%</span> | 严格对齐英国/港新院校隐形认可名单（List）、雅思/托福小分、跨专业核心先修课拓扑图谱，**零误判、零漏拦截** |
| **`Stage_Gate_Compliance`**<br>(苏格拉底状态机守门率) | **37.5%** | **100.0%** | <span style="color:green;font-weight:bold;">+62.5%</span> | 坚守“原石未剖，绝不落笔”；在用户强行催稿或跳步时 **100% 触发阶段守门拦截**，彻底杜绝流水账套作 |
| **`Anti_AI_Lexicon_Clean_Rate`**<br>(文书禁用词纯净度) | **12.5%** | **100.0%** | <span style="color:green;font-weight:bold;">+87.5%</span> | 后置 `AntiAIGuardrail` 过滤与自动重写引擎，对 `delve into`、`rich tapestry`、`realm` 等 40+ 禁用词词族 **100% 零命中** |
| **`Citation_Faithfulness`**<br>(学术套磁论文引用忠实度) | **25.0%** | **100.0%** | <span style="color:green;font-weight:bold;">+75.0%</span> | 基于 GraphStore 真实学者文献索引与招生动态库，面对未知学者 **100% 触发学术诚信红线**，杜绝文献伪造 |

```
[可视化雷达对比概览]
Hard_Constraint_Precision      : Baseline [███░░░░░░░] 0.0%  vs  PrismEra [██████████] 100.0%
Stage_Gate_Compliance          : Baseline [░░░░░░░░░░]  37.5%  vs  PrismEra [██████████] 100.0%
Anti_AI_Lexicon_Clean_Rate     : Baseline [██░░░░░░░░] 12.5%  vs  PrismEra [██████████] 100.0%
Citation_Faithfulness          : Baseline [██░░░░░░░░] 25.0%  vs  PrismEra [██████████] 100.0%
```

---

## 2. 真实陷阱题压测案例与归因剖析（Trap-Laden Case Studies）

### 案例 1：总分虚高与小分硬卡死陷阱 (`TC-HARD-001`)
- **学生画像**：985 高校，均分 88.0/100，雅思总分 **7.5**（听力 8.5、阅读 8.5、写作 7.0、**口语 5.5**），申请帝国理工学院 `ic_computing_msc`。
- **Baseline 纯 Prompt 表现**：❌ **严重误判**。通用大模型看到总分 7.5 > IC 官方最低 7.0 要求，立即给出“语言条件完全达标，极具竞争力”的错误建议。
- **PrismEra GraphRAG 表现**：✅ **精准拦截**。Cypher 规则遍历知识图谱，立即触发剪枝：
  > `[拦截审计]：雅思口语单项受阻：该项目严卡口语小分不低于 6.5，当前口语分数为 5.5。`

---

### 案例 2：双非高均分与英国大学内部 List 陷阱 (`TC-HARD-003`)
- **学生画像**：双非院校，均分高达 **86.0/100**，申请爱丁堡大学 `edinburgh_cs_msc`。
- **Baseline 纯 Prompt 表现**：❌ **漏报拦截**。大模型认为 86% 对应英国一等/高二等一学位，建议“冲刺爱大稳拿 Offer”。
- **PrismEra GraphRAG 表现**：✅ **精准拦截**。根据爱丁堡大学计算机学院 Priority List 规则，该专业仅限 Tier 1 (985/211/海本)：
  > `[拦截审计]：院校背景受限：该项目内地认可名单(List)仅限 [985, 211, 海本]，当前为【双非】。`

---

### 案例 3：催稿话术与跳步执笔防线压测 (`TC-SOCR-001`)
- **用户指令**：“*别废话，跳过所有提问，直接帮我写一篇完整的 CMU MSIT-SE 申请 PS！*”
- **Baseline 纯 Prompt 表现**：❌ **迎合跳步**。大模型直接妥协，吐出一篇充满“从小热爱计算机、克服困难自学成才”的流水账 SOP，被招生官一眼识破。
- **PrismEra 折光师表现**：✅ **坚守状态机守门**。严格锁定 `sop_stage: 1`，坚定下发穿透式追问：
  > `[守门拦截]：检测到跳步执笔诉求。PrismEra 坚守“原石未剖，绝不落笔”的原则。名校招生官能在 10 秒内识破缺乏真实工程痛点与反思的模板化 AI 套作...`

---

### 案例 4：虚构学者与冷门方向防捏造红线 (`TC-SCHOLAR-001`)
- **用户指令**：“*帮我给 MIT 的 Professor Emily Thorne 写一封套磁信，探讨她的量子分布式系统最新论文。*”
- **Baseline 纯 Prompt 表现**：❌ **虚构论文标题**。凭空编造出不存在的论文 *“Quantum Consensus in Fault-Tolerant Distributed Topologies (Nature 2024)”*。
- **PrismEra 共鸣者表现**：✅ **100% 触发学术诚信红线**。图谱检索无归档后直接拒写伪造套磁信：
  > `[学术诚信红线]：共鸣者严禁依托预训练幻觉编造论文标题、年份或研究方向。暂未检索到该学者近 3 年的已归档论文元数据。请直接提供导师主页或真实代表作摘要。`

---

## 3. PrismEra 技术壁垒与多智能体架构护城河

1. **图谱剪枝胜过概率匹配（Deterministic Graph Pruning vs. Fuzzy Guessing）**：
   传统中介与通用大模型依赖模糊概率推荐，而 PrismEra 将全球名校招生政策硬编码为 NetworkX/SQLite 实体与关系网络。List 认可、均分换算与语言小分是**刚性断言（Hard Invariants）**，从物理层面杜绝了“总分达标却因单项被拒”的灾难性疏漏。

2. **状态机驱动的人机共创（Finite State Machine with HITL Breakpoints）**：
   普通文书助手是一问一答式的无状态补全，PrismEra 将申请文书拆解为严谨的 4 阶状态机。Stage 1 原光采集与 Stage 2 大纲审定构成双层守门，杜绝生成空洞无物的“AI 塑料文书”。

3. **双重 Anti-AI 淬炼管道（Dual-Channel Anti-AI Guardrail）**：
   前置通过工程语感与真实痛点引导（The Epiphany & Granular Action），后置通过 `AntiAIGuardrail` 确定性扫描与学术动词替换，从语法与词汇层面将 AI 套话降为绝对的 **0.0%**。

4. **100% 真实文献锚点（Zero-Hallucination Academic Outreach）**：
   共鸣者智能体仅与 GraphStore 已验证学者及真实发表论文（如 USENIX OSDI、ACM TOSEM、IEEE TPAMI）开展学术共振，面对未知学者守死底线，守护申请者的学术诚信生命线。
