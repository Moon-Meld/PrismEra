"""End-to-end tests for the PrismEra LangGraph Orchestration Engine."""

from prismera.engine import PrismEraSession


def test_orchestrator_onboarding_and_unknown_intent():
    session = PrismEraSession(thread_id="test_onboarding")
    result = session.send_user_message("你好，我想了解一下你们平台")
    assert result["routing_decision"] == "DIRECT_ANSWER"
    assert "司光者" in result["latest_response"]


def test_pre_calibration_interception_for_locus():
    """Ironclad Rule 1: Missing 4 baseline parameters intercepts delegation to prism_locus."""
    session = PrismEraSession(thread_id="test_locus_intercept")
    # User asks for school positioning but provides NO background
    result = session.send_user_message("帮我看看我能申什么学校，做个选校定位")

    # Should be intercepted by Luminary
    assert result["routing_decision"] == "ASK_FOR_CLARIFICATION"
    assert result["active_agent"] is None
    assert "为了在万千学府中为你锁定不失真的落点焦距" in result["latest_response"]
    assert "本科院校" in result["latest_response"]


def test_complete_profile_delegation_to_locus():
    """When all 4 baseline parameters are satisfied, delegates to prism_locus."""
    session = PrismEraSession(thread_id="test_locus_success")
    msg = "我是浙江大学计算机专业，均分88分，想申请美研和英研CS项目，雅思7.5口语7.0，请帮我定校"
    result = session.send_user_message(msg)

    assert result["routing_decision"] == "DELEGATE_TO_AGENT"
    assert "prism_locus" in result["luminary_thought"]
    assert "定焦坐标系综述" in result["latest_response"]
    assert "远光·冲刺档" in result["latest_response"]
    assert "聚光·核心档" in result["latest_response"]
    assert "基光·稳妥档" in result["latest_response"]


def test_facet_diagnosis_node():
    session = PrismEraSession(thread_id="test_facet")
    result = session.send_user_message("请帮我诊断一下背景和成绩单，我均分86.5分，打算转专业申CS")

    assert result["routing_decision"] == "DELEGATE_TO_AGENT"
    assert "原石切面诊断" in result["latest_response"]
    assert "先修课图谱对齐表" in result["latest_response"]
    assert "倒计时打磨路线图" in result["latest_response"]


def test_disperser_socratic_state_machine():
    session = PrismEraSession(thread_id="test_disperser")
    # Stage 1: Socratic questions before draft
    result1 = session.send_user_message("帮我写CMU软件工程硕士的SOP文书")

    assert "Stage 1 原光采集与苏格拉底追问" in result1["latest_response"]
    assert "认知转折点" in result1["latest_response"]
    assert "颗粒度工程细节" in result1["latest_response"]

    # Provide details to advance to Stage 2
    detailed_reply = (
        "当时在做分布式高并发队列时遇到了网络分区导致的丢包问题，调试过程中发现传统心跳算法在15%丢包率下严重抖动，"
        "所以我设计了基于异步环形缓冲区的自适应调度器，优化了系统延迟和参数。"
    )
    result2 = session.send_user_message(detailed_reply)
    assert "Stage 2 光谱大纲构建" in result2["latest_response"]
    assert "入射角" in result2["latest_response"]
    assert "折射链条" in result2["latest_response"]


def test_resonator_synergy_and_academic_integrity():
    session = PrismEraSession(thread_id="test_resonator")
    # Real professor in KG
    result = session.send_user_message("想找UIUC的Indranil Gupta教授做2027年秋季博士套磁，帮我写一封Cold Email")

    assert result["routing_decision"] == "DELEGATE_TO_AGENT"
    assert "学术共振分析" in result["latest_response"]
    assert "220 词黄金标准套磁信" in result["latest_response"]
    assert "Adaptive Gossip Consensus" in result["latest_response"]

    # Unknown professor triggers academic integrity warning
    result_fake = session.send_user_message("帮我给不存在的教授John Smith写套磁信")
    assert "学术诚信警示" in result_fake["latest_response"]
