"""Unit tests for the Document Parser Tool and CLI upload workflow."""

import os
import tempfile
import pytest
from prismera.tools.document_parser import (
    parse_student_document,
    _evaluate_star_and_mining,
    _extract_prerequisite_courses,
)
from prismera.engine import PrismEraSession


SAMPLE_RESUME_TEXT = """# 个人简历

## 基本信息
- 姓名: 张同学
- 本科院校: 浙江大学 (985工程)
- 专业: 计算机科学与技术 (CS)
- 均分成绩: 88.5/100 (GPA 3.82/4.0)
- 语言成绩: 雅思 7.5 (听力 8.0, 阅读 8.5, 写作 6.5, 口语 7.0), GRE 325

## 核心主修与先修课程
| 课程名称 | 学分 | 成绩 |
| 高等数学 | 5.0 | 94 |
| 线性代数 | 3.0 | 91 |
| 概率论与数理统计 | 3.0 | 89 |
| 数据结构与算法 | 4.0 | 95 |
| 操作系统 | 4.0 | 88 |
| 计算机网络 | 3.5 | 86 |

## 科研与实习经历

### 1. 腾讯科技 - 分布式云平台研发实习生 (2025.06 - 2025.09)
负责微服务后台模块开发，参与了内部工单系统的数据库表设计与接口实现，协助团队完成单元测试，保障系统日常平稳运行。

### 2. 国家级大学生创新创业训练项目 - eBPF 自适应网络调度器 (2024.10 - 2025.04)
针对跨机架高延迟网络中传统心跳协议因丢包发生误判的痛点，设计了基于异步环形缓冲区的自适应调度器。在模拟15%丢包率的混沌工程测试中，将系统故障转移恢复延迟降低了28%，提升吞吐量达 15000 QPS。
"""


def test_parse_student_document_credentials():
    result = parse_student_document(SAMPLE_RESUME_TEXT)

    # 1. Credentials
    assert result["undergrad_name"] == "浙江大学"
    assert result["undergrad_tier"] == "985"
    assert "计算机" in result["major"]
    assert result["gpa_raw"] == "88.5/100"

    # 2. Language & GRE
    lang = result["language_scores"]
    assert lang["IELTS_total"] == 7.5
    assert lang["speaking"] == 7.0
    assert result["gre_gmat"] == {"GRE_total": 325}


def test_parse_prerequisite_courses():
    prereqs = _extract_prerequisite_courses(SAMPLE_RESUME_TEXT)
    assert "高等数学" in prereqs
    assert prereqs["高等数学"]["grade"] == "94"
    assert "数据结构与算法" in prereqs
    assert prereqs["数据结构与算法"]["grade"] == "95"
    assert "操作系统" in prereqs
    assert prereqs["操作系统"]["grade"] == "88"


def test_star_and_needs_mining_evaluation():
    # Experience 1: Vague, no metrics -> needs_mining=True
    vague_exp = "负责微服务后台模块开发，参与了内部工单系统的数据库表设计与接口实现，协助团队完成单元测试，保障系统日常平稳运行。"
    has_star_1, needs_mining_1, reason_1 = _evaluate_star_and_mining(vague_exp)
    assert has_star_1 is False
    assert needs_mining_1 is True
    assert "缺少量化产出数据" in reason_1

    # Experience 2: Rich technical actions + quantified metrics -> needs_mining=False
    solid_exp = "设计了基于异步环形缓冲区的自适应调度器。在模拟15%丢包率的混沌工程测试中，将系统故障转移恢复延迟降低了28%，提升吞吐量达 15000 QPS。"
    has_star_2, needs_mining_2, reason_2 = _evaluate_star_and_mining(solid_exp)
    assert has_star_2 is True
    assert needs_mining_2 is False
    assert "STAR细节完备" in reason_2 or "具备" in reason_2


def test_file_upload_and_state_synchronization():
    """Test importing document from file and synchronizing to StudentSpectrumProfile state tree."""
    with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as tf:
        tf.write(SAMPLE_RESUME_TEXT)
        tf_path = tf.name

    try:
        session = PrismEraSession(thread_id="test_upload_sync")
        profile_before = session.state["student_profile"]
        assert profile_before["undergrad_name"] is None

        # Upload document
        parsed = session.upload_document(tf_path)

        # Verify state tree was populated
        profile_after = session.state["student_profile"]
        assert profile_after["undergrad_name"] == "浙江大学"
        assert profile_after["undergrad_tier"] == "985"
        assert profile_after["gpa_raw"] == "88.5/100"
        assert "高等数学" in profile_after["prerequisite_grades"]
        assert len(profile_after["experiences"]) >= 2

        # Check needs_mining flags in state
        exps = profile_after["experiences"]
        assert any(e.get("needs_mining") is True for e in exps)
        assert any(e.get("needs_mining") is False for e in exps)

        # Check parsed_documents tracker
        assert os.path.basename(tf_path) in profile_after["parsed_documents"]

    finally:
        if os.path.exists(tf_path):
            os.remove(tf_path)
