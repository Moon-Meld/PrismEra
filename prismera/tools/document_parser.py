"""PrismEra Document Parser Tool.

Extracts structured applicant credentials, academic transcripts, prerequisite course grades,
and research/internship experiences from PDF transcripts, resumes, or markdown/text files.
Automatically assesses STAR completeness and flags experiences lacking metrics as needs_mining=True.
"""

from __future__ import annotations
import os
import re
import zlib
import subprocess
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class DocumentParseResult(BaseModel):
    """Structured extraction result from student resumes or transcripts."""
    undergrad_name: Optional[str] = Field(default=None, description="本科院校全称")
    undergrad_tier: Optional[str] = Field(default=None, description="院校梯队 (985/211/双非一本/海本)")
    major: Optional[str] = Field(default=None, description="本科所学专业")
    gpa_raw: Optional[str] = Field(default=None, description="原始均分或GPA标尺")
    language_scores: Dict[str, float] = Field(default_factory=dict, description="语言考试分数 (IELTS/TOEFL)")
    gre_gmat: Optional[Dict[str, int]] = Field(default=None, description="GRE/GMAT 分数")
    prerequisite_grades: Dict[str, Any] = Field(
        default_factory=dict,
        description="核心数学与计算机先修课成绩映射表"
    )
    experiences: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="科研与实习经历列表，含 STAR 完整度评估与 needs_mining 标记"
    )
    summary: str = Field(default="", description="档案解析概述与关键切面综述")
    raw_text_preview: str = Field(default="", description="原始文档内容前 500 字符预览")


def _decode_pdf_string(s: str) -> str:
    """Decodes standard PDF string escapes like octal escapes and special characters."""
    def replace_oct(m):
        try:
            return chr(int(m.group(1), 8))
        except Exception:
            return m.group(0)

    s = re.sub(r"\\([0-7]{1,3})", replace_oct, s)
    s = s.replace(r"\n", "\n").replace(r"\r", "\r").replace(r"\t", "\t")
    s = s.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")
    return s


def _extract_text_from_pdf_pure_python(pdf_bytes: bytes) -> str:
    """Pure-python fallback to extract text from uncompressed and FlateDecode PDF streams."""
    text_chunks: List[str] = []
    
    # 1. Look for all streams
    stream_pattern = re.compile(b"stream\r?\n(.*?)\r?\nendstream", re.DOTALL)
    for match in stream_pattern.finditer(pdf_bytes):
        stream_data = match.group(1)
        decompressed = b""
        try:
            decompressed = zlib.decompress(stream_data)
        except Exception:
            decompressed = stream_data  # Might already be plain text

        try:
            stream_text = decompressed.decode("utf-8", errors="ignore")
        except Exception:
            stream_text = decompressed.decode("latin-1", errors="ignore")

        # Extract text within BT ... ET blocks
        bt_blocks = re.findall(r"BT\s*(.*?)\s*ET", stream_text, re.DOTALL)
        for block in bt_blocks:
            # Match (text) Tj
            tj_matches = re.findall(r"\((.*?)\)\s*Tj", block)
            for m in tj_matches:
                text_chunks.append(_decode_pdf_string(m))
            # Match [(text1) (text2)] TJ
            array_matches = re.findall(r"\[(.*?)\]\s*TJ", block)
            for arr in array_matches:
                inner_strings = re.findall(r"\((.*?)\)", arr)
                text_chunks.append("".join(_decode_pdf_string(s) for s in inner_strings))

    # Also search for literal text in parenthesis
    if not text_chunks:
        direct_matches = re.findall(r"\(([A-Za-z0-9\u4e00-\u9fa5\s\.\,\:\-\_\/\%]+)\)", pdf_bytes.decode("utf-8", errors="ignore"))
        text_chunks.extend(direct_matches)

    return "\n".join(text_chunks)


def _read_document_text(
    file_path_or_text: Optional[str] = None,
    file_bytes: Optional[bytes] = None,
    file_name: Optional[str] = None,
) -> str:
    """Reads raw text from a file path (.pdf, .txt, .md), bytes, or returns text directly."""
    # 1. If bytes provided directly
    if file_bytes is not None:
        fn = (file_name or "").lower()
        if fn.endswith(".pdf") or file_bytes.startswith(b"%PDF"):
            # Try pypdf if installed
            try:
                import pypdf
                import io
                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
                if extracted.strip():
                    return extracted
            except Exception:
                pass
            # Pure python fallback
            extracted = _extract_text_from_pdf_pure_python(file_bytes)
            if extracted.strip():
                return extracted
            return ""

        # Plain text bytes
        for enc in ["utf-8", "gb18030", "gbk", "latin-1"]:
            try:
                return file_bytes.decode(enc)
            except Exception:
                continue
        return ""

    if file_path_or_text is None:
        return ""

    # If it's not a path or doesn't exist on disk, treat as raw text
    if not isinstance(file_path_or_text, str) or len(file_path_or_text) > 500 or "\n" in file_path_or_text:
        if not os.path.exists(file_path_or_text):
            return file_path_or_text

    if not os.path.exists(file_path_or_text):
        return file_path_or_text

    file_path = file_path_or_text
    lower_path = file_path.lower()

    if lower_path.endswith(".pdf"):
        # 1. Try pypdf if installed
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
            if extracted.strip():
                return extracted
        except Exception:
            pass

        # 2. Try system pdftotext
        try:
            proc = subprocess.run(
                ["pdftotext", file_path, "-"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return proc.stdout
        except Exception:
            pass

        # 3. Pure Python fallback
        try:
            with open(file_path, "rb") as f:
                pdf_data = f.read()
            extracted = _extract_text_from_pdf_pure_python(pdf_data)
            if extracted.strip():
                return extracted
        except Exception:
            pass

        return ""

    # Text files: UTF-8 with fallback to GB18030 / Latin-1
    for enc in ["utf-8", "gb18030", "gbk", "latin-1"]:
        try:
            with open(file_path, "r", encoding=enc) as f:
                return f.read()
        except Exception:
            continue

    return ""


# Universities dictionary for matching
CHINESE_UNIVERSITIES = [
    ("清华大学", "985"), ("北京大学", "985"), ("浙江大学", "985"), ("浙大", "985"),
    ("上海交通大学", "985"), ("上交", "985"), ("复旦大学", "985"), ("复旦", "985"),
    ("南京大学", "985"), ("南大", "985"), ("中国科学技术大学", "985"), ("中科大", "985"),
    ("哈尔滨工业大学", "985"), ("哈工大", "985"), ("西安交通大学", "985"), ("西交", "985"),
    ("华中科技大学", "985"), ("华科", "985"), ("武汉大学", "985"), ("武大", "985"),
    ("北京航空航天大学", "985"), ("北航", "985"), ("同济大学", "985"), ("同济", "985"),
    ("东南大学", "985"), ("中南大学", "985"), ("中山大学", "985"), ("电子科技大学", "985"), ("成电", "985"),
    ("北京邮电大学", "211"), ("北邮", "211"), ("西安电子科技大学", "211"), ("西电", "211"),
    ("华东师范大学", "985"), ("吉林大学", "985"), ("大连理工大学", "985"), ("山东大学", "985"),
    ("湖南大学", "985"), ("重庆大学", "985"), ("四川大学", "985"), ("川大", "985"),
    ("厦门大学", "985"), ("南开大学", "985"), ("天津大学", "985"), ("北京理工大学", "985"), ("北理工", "985"),
    ("华南理工大学", "985"), ("中国人民大学", "985"), ("人大", "985"),
    ("苏州大学", "211"), ("上海大学", "211"), ("武汉理工大学", "211"), ("北京工业大学", "211"),
]

# Prerequisite course definitions
CORE_PREQUISITE_DEFINITIONS = [
    ("高等数学", ["高等数学", "微积分", "Calculus", "高数"]),
    ("线性代数", ["线性代数", "高等代数", "Linear Algebra", "线代"]),
    ("概率论与数理统计", ["概率论与数理统计", "概率论", "数理统计", "Probability", "Statistics"]),
    ("离散数学", ["离散数学", "Discrete Mathematics"]),
    ("数据结构与算法", ["数据结构与算法", "数据结构", "Data Structures", "算法设计与分析", "Algorithms"]),
    ("操作系统", ["操作系统", "Operating Systems", "OS"]),
    ("计算机组成原理", ["计算机组成原理", "计算机体系结构", "Computer Architecture", "Computer Organization"]),
    ("计算机网络", ["计算机网络", "Computer Networks", "计网"]),
    ("面向对象程序设计", ["面向对象程序设计", "面向对象", "C++程序设计", "Java程序设计", "Python程序设计", "Object-Oriented"]),
    ("数据库系统", ["数据库系统", "数据库概论", "Database Systems", "数据库原理"]),
    ("编译原理", ["编译原理", "Compiler Principles"]),
    ("机器学习", ["机器学习", "深度学习", "人工智能", "Machine Learning", "Deep Learning", "Artificial Intelligence"]),
]


def _extract_school_and_major(text: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract undergrad school name, tier, and major."""
    name: Optional[str] = None
    tier: Optional[str] = None
    major: Optional[str] = None

    # School
    for u_name, u_tier in CHINESE_UNIVERSITIES:
        if u_name in text:
            name = u_name if len(u_name) > 2 else next((u[0] for u in CHINESE_UNIVERSITIES if u_name in u[0] and len(u[0]) > 2), u_name)
            tier = u_tier
            break

    if not name:
        # Check tier keywords
        if "985" in text:
            tier = "985"
        elif "211" in text:
            tier = "211"
        elif "双非" in text:
            tier = "双非一本"
        elif any(k in text for k in ["海本", "美本", "英本", "加本", "港本"]):
            tier = "海本"

        # Check overseas universities
        for ov_school in ["UC Berkeley", "UCLA", "UIUC", "CMU", "NYU", "UCL", "IC", "NUS", "NTU", "HKU", "HKUST"]:
            if ov_school.lower() in text.lower():
                name = ov_school
                tier = "海本"
                break

    # Major
    major_candidates = [
        ("计算机科学与技术 (CS)", ["计算机科学与技术", "计算机科学", "计算机工程", "计科", "computer science", "cs"]),
        ("软件工程 (SE)", ["软件工程", "software engineering", "se"]),
        ("数据科学与大数据 (DS)", ["数据科学与大数据技术", "数据科学", "data science", "ds"]),
        ("人工智能 (AI)", ["人工智能", "智能科学与技术", "artificial intelligence", "ai"]),
        ("商业分析 (BA)", ["商业分析", "business analytics", "ba"]),
        ("电子信息工程 (EE)", ["电子信息工程", "电子工程", "信息工程", "electrical engineering", "ee"]),
        ("自动化", ["自动化", "automation", "控制科学与工程"]),
        ("信息与计算科学", ["信息与计算科学", "数学与应用数学", "应用数学", "mathematics"]),
    ]
    for m_std, kws in major_candidates:
        if any(kw in text.lower() for kw in kws):
            major = m_std
            break

    return name, tier, major


def _extract_gpa_and_scores(text: str) -> tuple[Optional[str], Dict[str, float], Optional[Dict[str, int]]]:
    """Extract raw GPA, IELTS/TOEFL scores, and GRE/GMAT scores."""
    gpa_raw: Optional[str] = None
    lang_scores: Dict[str, float] = {}
    gre_gmat: Optional[Dict[str, int]] = None

    # GPA
    # e.g., 均分成绩: 88.5/100, 均分: 88.5, 88.5/100, 3.82/4.0, 加权平均分 89
    gpa_hundred = re.search(
        r"(?:均分成绩|加权平均成绩|加权均分|加权平均分|平均分|均分|GPA|成绩)[:：\s]*(\d{2}(?:\.\d+)?)\s*(?:分|/100)?",
        text,
        re.IGNORECASE,
    )
    if gpa_hundred:
        score_val = float(gpa_hundred.group(1))
        if 60 <= score_val <= 100:
            gpa_raw = f"{score_val}/100"

    # Also check direct "88.5/100" pattern anywhere
    if not gpa_raw:
        match_slash = re.search(r"(\d{2}(?:\.\d+)?)/100", text)
        if match_slash:
            gpa_raw = f"{match_slash.group(1)}/100"

    if not gpa_raw:
        gpa_four = re.search(r"(?:GPA|绩点)[:：\s]*([234]\.\d{1,2})\s*(?:/4\.0)?", text, re.IGNORECASE)
        if gpa_four:
            gpa_raw = f"{gpa_four.group(1)}/4.0"
        else:
            match_slash_4 = re.search(r"([234]\.\d{1,2})/4\.0", text)
            if match_slash_4:
                gpa_raw = f"{match_slash_4.group(1)}/4.0"

    # Language scores: IELTS
    ielts_match = re.search(r"雅思|IELTS", text, re.IGNORECASE)
    if ielts_match:
        total_m = re.search(r"(?:雅思|IELTS)[:：\s]*(?:总分[:：\s]*)?([56789](?:\.[05])?)", text, re.IGNORECASE)
        if total_m:
            lang_scores["IELTS_total"] = float(total_m.group(1))
        spk_m = re.search(r"口语[:：\s]*([56789](?:\.[05])?)", text)
        if spk_m:
            lang_scores["speaking"] = float(spk_m.group(1))
        list_m = re.search(r"听力[:：\s]*([56789](?:\.[05])?)", text)
        if list_m:
            lang_scores["listening"] = float(list_m.group(1))
        read_m = re.search(r"阅读[:：\s]*([56789](?:\.[05])?)", text)
        if read_m:
            lang_scores["reading"] = float(read_m.group(1))
        wrt_m = re.search(r"写作[:：\s]*([56789](?:\.[05])?)", text)
        if wrt_m:
            lang_scores["writing"] = float(wrt_m.group(1))

    # TOEFL
    toefl_match = re.search(r"托福|TOEFL", text, re.IGNORECASE)
    if toefl_match:
        t_total = re.search(r"(?:托福|TOEFL)[:：\s]*(?:总分[:：\s]*)?(\d{2,3})", text, re.IGNORECASE)
        if t_total:
            lang_scores["TOEFL_total"] = float(t_total.group(1))
        t_spk = re.search(r"(?:托福口语|S|Speaking)[:：\s]*(\d{1,2})", text, re.IGNORECASE)
        if t_spk:
            lang_scores["speaking"] = float(t_spk.group(1))

    # GRE
    gre_match = re.search(r"GRE[:：\s]*(\d{3})", text, re.IGNORECASE)
    if gre_match:
        gre_gmat = {"GRE_total": int(gre_match.group(1))}

    return gpa_raw, lang_scores, gre_gmat


def _extract_prerequisite_courses(text: str) -> Dict[str, Any]:
    """Extract core mathematics and CS prerequisite course grades from transcript tables or text."""
    prereqs: Dict[str, Any] = {}
    lines = text.splitlines()

    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue

        # Case 1: Table format with pipe delimiters (| course | credits | score |)
        if "|" in line_clean:
            cells = [c.strip() for c in line_clean.split("|") if c.strip()]
            for std_course_name, alias_list in CORE_PREQUISITE_DEFINITIONS:
                if std_course_name in prereqs:
                    continue
                matched_alias = None
                matched_idx = -1
                for idx, cell in enumerate(cells):
                    for alias in alias_list:
                        if alias.lower() in cell.lower():
                            matched_alias = alias
                            matched_idx = idx
                            break
                    if matched_alias:
                        break

                if matched_alias and matched_idx >= 0:
                    subsequent = cells[matched_idx + 1 :]
                    grade_val = None
                    # Search reversed to pick score column over credit column
                    for c in reversed(subsequent):
                        c_num = c.replace("分", "").strip()
                        if re.match(r"^\d{2}(?:\.\d+)?$", c_num):
                            num = float(c_num)
                            if 50 <= num <= 100:
                                grade_val = c_num
                                break
                        elif re.match(r"^[ABCD][\+\-]?$", c_num, re.IGNORECASE):
                            grade_val = c_num.upper()
                            break
                        elif re.match(r"^[234]\.\d{1,2}$", c_num):
                            grade_val = c_num
                            break
                    if not grade_val and subsequent:
                        grade_val = subsequent[-1]

                    if grade_val:
                        prereqs[std_course_name] = {
                            "matched_name": matched_alias,
                            "grade": grade_val,
                            "verified": True,
                        }
            continue

        # Case 2: Plain text lines (e.g. "高等数学: 94分" or "线性代数 91")
        for std_course_name, alias_list in CORE_PREQUISITE_DEFINITIONS:
            if std_course_name in prereqs:
                continue
            for alias in alias_list:
                if alias.lower() in line_clean.lower():
                    # Look for numerical score
                    score_m = re.search(r"(\d{2}(?:\.\d+)?)\s*(?:分|/100)?", line_clean)
                    if score_m and 50 <= float(score_m.group(1)) <= 100:
                        prereqs[std_course_name] = {
                            "matched_name": alias,
                            "grade": score_m.group(1),
                            "verified": True,
                        }
                        break
                    letter_m = re.search(r"\b([ABCD][\+\-]?)\b", line_clean)
                    if letter_m:
                        prereqs[std_course_name] = {
                            "matched_name": alias,
                            "grade": letter_m.group(1),
                            "verified": True,
                        }
                        break

    return prereqs


def _evaluate_star_and_mining(exp_text: str) -> tuple[bool, bool, str]:
    """Evaluate whether an experience has complete STAR details and quantitative metrics.

    Returns:
        (has_star_details, needs_mining, reason)
    """
    clean_text = exp_text.strip()
    if len(clean_text) < 40:
        return False, True, "描述过于简短，缺乏具体职责、技术动作与产出量化。"

    # Check for quantitative indicators (numbers, %, ms, QPS, 提升, 降低, 倍)
    has_metrics = bool(
        re.search(r"(\d+(?:\.\d+)?%|\d+\s*(?:ms|毫秒|秒|s|qps|tps|w|万|k)|提升|降低|减少|增长|并发|吞吐)", clean_text, re.IGNORECASE)
    )

    # Check for granular technical actions (architecture, algorithm, refactor, debug, protocol, eBPF, pipeline, etc.)
    has_granular_action = bool(
        re.search(
            r"(设计|重构|实现|优化|研发|架构|调度|算法|排查|调试|自适应|缓冲区|管道|模型|训练|部署|微服务|内核|协议|缓存|索引|并发|容错|吞吐)",
            clean_text
        )
    )

    # Check for situational context / problem boundary (遇到, 瓶颈, 失败, 丢包, 延迟, 挑战, 极端情况, 场景)
    has_situation_challenge = bool(
        re.search(r"(遇到|面临|瓶颈|挑战|故障|抖动|丢包|延迟|网络分区|死锁|边界|高并发|针对|背景)", clean_text)
    )

    # STAR complete requires: (Situation/Challenge or Task) + Granular Action + Quantified Metrics
    if has_metrics and has_granular_action and has_situation_challenge:
        return True, False, "STAR细节完备，具备可信的量化工程结果与技术权衡。"
    elif has_metrics and has_granular_action:
        return True, False, "具备清晰的技术方案与可量化产出。"
    else:
        reasons: List[str] = []
        if not has_metrics:
            reasons.append("缺少量化产出数据（如延迟降低%、QPS指标或性能对比）")
        if not has_granular_action:
            reasons.append("技术动作模糊（缺少具体模块实现、算法或调优细节）")
        if not has_situation_challenge:
            reasons.append("未说明所面临的技术困境或边界条件")

        reason_str = "，".join(reasons) + "；需【折光师】通过苏格拉底追问深度挖掘认知转折与硬核细节。"
        return False, True, reason_str


def _extract_experiences(text: str) -> List[Dict[str, Any]]:
    """Segment and extract research and internship experiences, evaluating STAR completeness."""
    experiences: List[Dict[str, Any]] = []

    # Section markers supporting combined and single headers
    sections = re.split(
        r"(?:^|\n)(?:#+\s*|\*+\s*|【\s*)?(科研(?:与|及)?实习(?:经历)?|科研经历|项目经历|实习经历|工作经历|实践经历|工程项目|项目与实习|Research Experience|Internship Experience|Internship|Work Experience|Projects)[\s*】:]*",
        text,
        flags=re.IGNORECASE
    )

    extracted_blocks: List[str] = []
    if len(sections) > 1:
        # Sections were matched: extract bodies of experience sections
        for i in range(1, len(sections), 2):
            sec_title = sections[i]
            sec_body = sections[i + 1] if i + 1 < len(sections) else ""
            extracted_blocks.append(f"{sec_title}\n{sec_body}")
    else:
        # If no explicit major headers found, look for bullet points or project headers
        extracted_blocks = [text]

    for block in extracted_blocks:
        # Split individual projects by subheaders (e.g. "###", "1.", "【", "202x")
        sub_items = re.split(r"(?:^|\n)(?:###|\d+\.|\-|\*|【)\s*", block)
        for item in sub_items:
            item_clean = item.strip()
            if len(item_clean) < 30:
                continue

            first_line = item_clean.splitlines()[0].strip()
            # Exclude top-level document headers
            if any(first_line.startswith(h) for h in ["# 个人简历", "# 申请者", "# 简历", "## 基本信息", "## 核心", "## 教育", "姓名", "均分"]):
                continue

            # Check if this item looks like an experience entry
            if not any(k in item_clean for k in ["项目", "实习", "系统", "开发", "研发", "研究", "算法", "平台", "实验室", "工程", "架构", "设计"]):
                continue

            # Clean title
            title = first_line.lstrip("#* \t")[:60]
            date_match = re.search(r"(\d{4}[年\.\-/]\d{1,2}(?:\s*[-~至到]\s*(?:\d{4}[年\.\-/]\d{1,2}|至今|现在|Present))?)", item_clean)
            period = date_match.group(1) if date_match else "在校期间"

            # Evaluate STAR
            has_star, needs_mining, reason = _evaluate_star_and_mining(item_clean)

            experiences.append({
                "title": title,
                "period": period,
                "raw_content": item_clean,
                "has_star_details": has_star,
                "needs_mining": needs_mining,
                "mining_reason": reason,
            })

    return experiences


def parse_student_document(
    file_path_or_text: Optional[str] = None,
    file_bytes: Optional[bytes] = None,
    file_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Main document parsing function.

    Parses student resume or transcript text / PDF into a structured schema,
    extracting institution, major, GPA, prerequisite grades, and assessing STAR details.
    Supports file path, raw string content, or raw bytes directly.
    """
    raw_text = _read_document_text(
        file_path_or_text=file_path_or_text,
        file_bytes=file_bytes,
        file_name=file_name
    )
    if not raw_text.strip():
        # Empty or unreadable document
        empty_res = DocumentParseResult(
            summary="无法从提供的路径或文本中读取有效字符，请检查文件权限或格式。",
            raw_text_preview=""
        )
        return empty_res.model_dump()

    # 1. School, tier, major
    school_name, school_tier, major = _extract_school_and_major(raw_text)

    # 2. GPA & language & GRE
    gpa_raw, lang_scores, gre_gmat = _extract_gpa_and_scores(raw_text)

    # 3. Core prerequisite course grades
    prereq_grades = _extract_prerequisite_courses(raw_text)

    # 4. Research & internship experiences
    experiences = _extract_experiences(raw_text)

    # 5. Build summary narrative
    school_desc = f"{school_name or '未明确高校'} ({school_tier or '待核定'})"
    gpa_desc = gpa_raw or "未明确均分"
    prereq_count = len(prereq_grades)
    mining_needed_count = sum(1 for exp in experiences if exp.get("needs_mining"))

    summary = (
        f"解析完成：提取到本科背景【{school_desc} · {major or '专业待定'}】，"
        f"均分/GPA【{gpa_desc}】；对齐核心先修课 {prereq_count} 门；"
        f"结构化经历 {len(experiences)} 项（其中 {mining_needed_count} 项缺乏量化细节，已标记为待折光挖掘）。"
    )

    result = DocumentParseResult(
        undergrad_name=school_name,
        undergrad_tier=school_tier,
        major=major,
        gpa_raw=gpa_raw,
        language_scores=lang_scores,
        gre_gmat=gre_gmat,
        prerequisite_grades=prereq_grades,
        experiences=experiences,
        summary=summary,
        raw_text_preview=raw_text[:500].strip(),
    )

    return result.model_dump()
