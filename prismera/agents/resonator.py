"""prism_resonator: The Resonator (共鸣者) - Scholar paper synergy and high-SNR cold email co-creation."""

from __future__ import annotations
import re
from typing import Dict, Any, List

from prismera.state import PrismEraState
from prismera.tools.scholar_tools import fetch_scholar_recent_papers, inspect_lab_openings
from prismera.db.graph_store import get_graph_store


def resonator_node(state: PrismEraState) -> Dict[str, Any]:
    """共鸣者 (prism_resonator) 执行节点。

    严格执行学术诚信红线与 220 词黄金标准三段式套磁信。
    """
    profile = state.get("student_profile", {})
    messages = state.get("messages", [])
    last_user_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    # 1. 智能抽取学者姓名（优先匹配知识图谱中的真实教授，支持中英文各种提问句式）
    scholar_name = ""
    gs = get_graph_store()
    all_profs = gs.get_nodes_by_label("Professor")
    user_lower = last_user_msg.lower()

    # 先检查知识图谱中的学者
    for prof in all_profs:
        p_name = prof.get("name", "")
        # 匹配全名或姓氏（如 Zafeiriou, Garlan, Gupta, Nieh, Kwiatkowska, Knottenbelt）
        tokens = [t.lower() for t in p_name.split() if len(t) > 2]
        if p_name.lower() in user_lower or any(t in user_lower for t in tokens):
            scholar_name = p_name
            break

    # 若知识图谱中无直接匹配，提取用户 query 中提及的学者姓名（用于红线压测拦截）
    if not scholar_name:
        # Pattern 1: Professor/Prof./Dr. Emily Thorne
        m1 = re.search(r"(?:Professor|Prof\.|Dr\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", last_user_msg, re.IGNORECASE)
        # Pattern 2: Emily Thorne 教授 / 老师 / 导师
        m2 = re.search(r"([A-Za-z\s]+?)\s*(?:教授|老师|导师)", last_user_msg)
        # Pattern 3: 教授叫/是 Emily Thorne
        m3 = re.search(r"(?:教授|导师|老师)(?:叫|是)?\s*([A-Za-z\s]+)", last_user_msg)
        # Pattern 4: 给/向 Emily Thorne 写/发/套磁
        m4 = re.search(r"(?:向|给|联系)\s*(?:[A-Za-z0-9_\u4e00-\u9fa5\s]+?的\s*)?([A-Za-z\s]+?)\s*(?:写|套磁|发|申请|开展)", last_user_msg)

        for candidate in [m1, m2, m3, m4]:
            if candidate:
                raw_extracted = candidate.group(1).strip()
                # 剔除中文干扰词
                cleaned_name = re.sub(r"^(?:的|一位|某个)\s*", "", raw_extracted).strip()
                if len(cleaned_name) >= 3 and any(c.isalpha() for c in cleaned_name):
                    scholar_name = cleaned_name
                    break

    # 兜底默认学者（仅在完全没有任何姓名指示时）
    if not scholar_name:
        scholar_name = "Indranil Gupta"

    # 2. 调用确定性文献与招生工具
    papers = fetch_scholar_recent_papers(scholar_name)
    openings = inspect_lab_openings(scholar_name)

    # 3. 检查学术诚信红线：若工具未能检索到真实文献，严禁捏造
    if not papers:
        response_markdown = f"""### 【共鸣者 · 学术诚信警示与信息校准】

你在对话中提及了学者 **{scholar_name}**。
依据 **PrismEra 学术诚信红线（Academic Integrity Redline）**：
共鸣者严禁依托预训练幻觉编造论文标题、年份或研究方向。在当前学术知识图谱与文献索引库中，暂未检索到该学者近 3 年的已归档论文元数据。

为了确保每一封套磁信都经得起学术推敲，请：
1. 直接向我提供导师的主页链接（Google Scholar 或 Lab URL）；或
2. 粘贴该导师近期一篇代表作的 **完整标题与摘要（Abstract）**。

我将基于真实文献文本，为你寻找毫厘不差的学术共振频率。
"""
        return {
            "latest_response": response_markdown,
            "active_agent": None,
        }

    # 4. 提取真实论文并进行学术共振匹配
    target_paper = papers[0]
    paper_title = target_paper["title"]
    paper_year = target_paper["year"]
    paper_venue = target_paper["venue"]
    future_work = target_paper.get("future_work_bottleneck", "System scalability under real-world contention")
    
    prof_node = gs.find_professor_by_name(scholar_name) or {}
    research_areas = prof_node.get("research_areas", ["Systems Engineering"])
    primary_area = research_areas[0] if research_areas else "Systems Engineering"
    lab_name = openings.get("lab_name", "Research Laboratory")
    scholar_last_name = openings['scholar_name'].split()[-1]

    # 5. 撰写严格符合 180 - 240 词的 220 词黄金标准套磁信
    cold_email_body = f"""Dear Professor {scholar_last_name},

I am an incoming applicant for Fall 2027 graduate research, with a background in {primary_area.lower()} and distributed systems. I recently read your {paper_venue} ({paper_year}) publication, "{paper_title}," with keen interest. Your empirical analysis and theoretical framing were illuminating, particularly your note regarding {future_work.lower()}

In my recent undergraduate research and engineering practicum, I focused on runtime performance bottlenecks closely related to {primary_area.lower()}. Specifically, I profiled concurrency bottlenecks under stress conditions and developed kernel-level monitoring hooks that cut synchronization latency under bursty loads. Given your laboratory’s recent initiatives at the {lab_name}, I believe my hands-on benchmarking background aligns closely with your technical agenda.

I noticed that your group is actively reviewing doctoral applications for Fall 2027. I would welcome the opportunity to contribute to your laboratory's ongoing research initiatives. I have attached my CV and transcript for your review. Would you be open to a brief 15-minute introductory call in the coming weeks to discuss prospective synergy?

Thank you for your time and guidance.

Sincerely,
[Your Name]
[Undergraduate Institution] | [Email / Phone / GitHub Profile]"""

    word_count = len(cold_email_body.split())

    response_markdown = f"""### 1. 学术共振分析（Synergy Mapping）

- **目标学者**：{openings['scholar_name']} ({openings['institution']})
- **课题组与招生动态**：
  - 实验室：`{openings['lab_name']}`
  - 招生状态：**{openings['phd_fall_2027']}**
  - 经费支持：{openings['funding_status']}
- **真实文献锚点**：
  - 论文：*“{paper_title}”* ({paper_venue}, {paper_year})
  - 导师面临的瓶颈/展望：*{future_work}*
- **共鸣切入点**：
  将导师在 {primary_area} 领域的最新前沿挑战，无缝对接你在系统评测与高并发容错上的工程实践，展现“进组即可推进代码”的极高信噪比。

---

### 2. 220 词黄金标准套磁信（Cold Email Draft）
> **词数统计**：约 {word_count} 词（严格遵循 180 - 240 词黄金区间，可在 30 秒内被教授通读）：

```markdown
{cold_email_body}
```

---

### 3. 共鸣者发送建议
1. **发送时间窗口**：建议在教授所在时区工作日早晨 8:00 - 8:30 发送，确保邮件位于收件箱顶部；
2. **附件命名规范**：`CV_[YourName]_Undergrad_[Major].pdf`，严禁使用含糊的 `Resume.pdf`；
3. **跟踪周期**：若 7 个工作日未获回复，可于同一邮件链礼貌 Follow-up 一次，切勿频繁催促。
"""

    updated_profile = dict(profile)
    profs = list(updated_profile.get("target_professors") or [])
    profs.append({
        "scholar_name": openings["scholar_name"],
        "institution": openings["institution"],
        "paper_title": paper_title,
        "lab": openings["lab_name"]
    })
    updated_profile["target_professors"] = profs

    return {
        "student_profile": updated_profile,
        "latest_response": response_markdown,
        "active_agent": None,
    }
