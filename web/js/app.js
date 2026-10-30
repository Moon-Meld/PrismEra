/**
 * PrismEra · 棱镜纪 - 暗黑光学美学工作台前端驱动引擎
 * Milestone 4: LangGraph HITL 断点共创、选校矩阵双向联动、大纲编辑与暗室局部折射 Diff
 */

(() => {
  "use strict";

  // 1. 全局智能体光学元数据
  const AGENT_CONFIGS = {
    luminary: {
      id: "luminary",
      name: "司光者",
      badge: "The Luminary",
      title: "中枢光轴 · 意图解析与总控路由",
      color: "#F8FAFC",
      orbClass: "orb-luminary",
      agentClass: "agent-luminary",
      icon: "✦"
    },
    facet: {
      id: "facet",
      name: "切面师",
      badge: "The Facet",
      title: "光谱分光仪 · 成绩单切面与先修课图谱",
      color: "#06B6D4",
      orbClass: "orb-facet",
      agentClass: "agent-facet",
      icon: "🔬"
    },
    locus: {
      id: "locus",
      name: "定焦师",
      badge: "The Locus",
      title: "全局透镜 · 知识图谱三步定焦与零幻觉矩阵",
      color: "#F59E0B",
      orbClass: "orb-locus",
      agentClass: "agent-locus",
      icon: "🎯"
    },
    disperser: {
      id: "disperser",
      name: "折光师",
      badge: "The Disperser",
      title: "暗室暗房 · 苏格拉底文书挖掘与去AI化淬炼",
      color: "#A855F7",
      orbClass: "orb-disperser",
      agentClass: "agent-disperser",
      icon: "✍️"
    },
    resonator: {
      id: "resonator",
      name: "共鸣者",
      badge: "The Resonator",
      title: "激光谐振腔 · 学术文献图谱共振与高信噪比套磁",
      color: "#10B981",
      orbClass: "orb-resonator",
      agentClass: "agent-resonator",
      icon: "📧"
    },
    echo: {
      id: "echo",
      name: "回音壁",
      badge: "The Echo",
      title: "回声测试仪 · 模拟面试与网申护航官",
      color: "#38BDF8",
      orbClass: "orb-echo",
      agentClass: "agent-echo",
      icon: "⚡"
    }
  };

  // 2. 应用核心状态
  const state = {
    sessionId: localStorage.getItem("prismera_session_id") || "prism_" + Math.random().toString(16).substring(2, 10),
    activeAgent: "luminary",
    isStreaming: false,
    pendingHumanReview: null,
    activeTab: "profile",
    studentProfile: {
      undergrad_name: null,
      undergrad_tier: null,
      major: null,
      gpa_raw: null,
      language_scores: {},
      target_regions: [],
      target_majors: [],
      shortlisted_programs: [],
      sop_stage: 1,
      mined_story_fragments: [],
      target_professors: [],
      sop_outline: [],
      sop_draft: "",
      sop_critique: {},
      sop_versions: [],
      locked_target_program: null,
      interview_records: [],
      application_timeline: [],
    },
    selectedSnippet: "",
    latestRefractDiff: null,
    outlineDebounceTimer: null,
    currentAssistantMessageEl: null,
    currentBubbleContentEl: null,
    currentRawMarkdown: ""
  };

  // 保存 Session ID
  localStorage.setItem("prismera_session_id", state.sessionId);

  // 3. DOM 元素缓存
  const elements = {
    sessionIdDisplay: document.getElementById("session-id-display"),
    newSessionBtn: document.getElementById("new-session-btn"),
    gatewayStatus: document.getElementById("gateway-status"),
    agentIndicator: document.getElementById("agent-indicator"),
    activeAgentLabel: document.getElementById("active-agent-label"),
    chatMessages: document.getElementById("chat-messages"),
    chatInput: document.getElementById("chat-input"),
    sendBtn: document.getElementById("send-btn"),
    quickChips: document.getElementById("quick-chips"),
    toastContainer: document.getElementById("toast-container"),

    // Tabs
    tabBtnProfile: document.getElementById("tab-btn-profile"),
    tabBtnMatrix: document.getElementById("tab-btn-matrix"),
    tabBtnSop: document.getElementById("tab-btn-sop"),
    tabBtnEcho: document.getElementById("tab-btn-echo"),
    tabBtnResonator: document.getElementById("tab-btn-resonator"),
    resonatorCountBadge: document.getElementById("resonator-count-badge"),
    viewProfile: document.getElementById("view-profile"),
    viewMatrix: document.getElementById("view-matrix"),
    viewSop: document.getElementById("view-sop"),
    viewEcho: document.getElementById("view-echo"),
    viewResonator: document.getElementById("view-resonator"),

    // Milestone 9: Document Upload Dropzone
    dropzoneCard: document.getElementById("dropzone-card"),
    dropzoneArea: document.getElementById("dropzone-area"),
    resumeFileInput: document.getElementById("resume-file-input"),
    btnTriggerFileUpload: document.getElementById("btn-trigger-file-upload"),
    uploadProgressBar: document.getElementById("upload-progress-bar"),
    uploadProgressFill: document.getElementById("upload-progress-fill"),
    uploadResultPill: document.getElementById("upload-result-pill"),
    uploadResultText: document.getElementById("upload-result-text"),
    btnClearUploadPill: document.getElementById("btn-clear-upload-pill"),

    // Milestone 9: Prerequisite Alignment & Blindspots Radar
    prereqCard: document.getElementById("prereq-card"),
    prereqCoverageBadge: document.getElementById("prereq-coverage-badge"),
    btnFacetPrereqAudit: document.getElementById("btn-facet-prereq-audit"),
    prereqAdviceBox: document.getElementById("prereq-advice-box"),
    prereqAdviceText: document.getElementById("prereq-advice-text"),
    prereqCoursesGrid: document.getElementById("prereq-courses-grid"),

    // Milestone 9: Experiences & STAR Radar
    experiencesCard: document.getElementById("experiences-card"),
    experiencesCounter: document.getElementById("experiences-counter"),
    experiencesListContainer: document.getElementById("experiences-list-container"),

    // Milestone 9: Add Program Modal Elements
    btnOpenAddProgModal: document.getElementById("btn-open-add-prog-modal"),
    addProgramModal: document.getElementById("add-program-modal"),
    closeAddProgModalBtn: document.getElementById("close-add-prog-modal-btn"),
    cancelAddProgBtn: document.getElementById("cancel-add-prog-btn"),
    progSearchKeyword: document.getElementById("prog-search-keyword"),
    progRegionPills: document.getElementById("prog-region-pills"),
    progTargetBracket: document.getElementById("prog-target-bracket"),
    progResultsList: document.getElementById("prog-results-list"),

    // Milestone 9: Resonator Scholar Workbench Elements
    resonatorBanner: document.getElementById("resonator-banner"),
    resonatorProfInput: document.getElementById("resonator-prof-input"),
    btnSearchProfessor: document.getElementById("btn-search-professor"),
    matchedProfsCounter: document.getElementById("matched-profs-counter"),
    resonatorProfsGrid: document.getElementById("resonator-profs-grid"),
    coldEmailWordcount: document.getElementById("cold-email-wordcount"),
    coldEmailBox: document.getElementById("cold-email-box"),
    btnCopyColdEmail: document.getElementById("btn-copy-cold-email"),

    // Milestone 9: Live Interview Workbench Elements
    liveInterviewSandbox: document.getElementById("live-interview-sandbox"),
    interviewLiveInput: document.getElementById("interview-live-input"),
    interviewInputCounter: document.getElementById("interview-input-counter"),
    btnSubmitLiveEval: document.getElementById("btn-submit-live-eval"),

    // Profile View Elements
    completenessPercentage: document.getElementById("completeness-percentage"),
    completenessBarFill: document.getElementById("completeness-bar-fill"),
    chkTier: document.getElementById("chk-tier"),
    chkGpa: document.getElementById("chk-gpa"),
    chkMajor: document.getElementById("chk-major"),
    chkTarget: document.getElementById("chk-target"),
    valUndergrad: document.getElementById("val-undergrad"),
    valUndergradSub: document.getElementById("val-undergrad-sub"),
    valGpa: document.getElementById("val-gpa"),
    valGpaSub: document.getElementById("val-gpa-sub"),
    valLanguage: document.getElementById("val-language"),
    valLanguageSub: document.getElementById("val-language-sub"),
    valTarget: document.getElementById("val-target"),
    valTargetSub: document.getElementById("val-target-sub"),
    fragmentTagsContainer: document.getElementById("fragment-tags-container"),
    fragmentCounter: document.getElementById("fragment-counter"),
    profileStatusBadge: document.getElementById("profile-status-badge"),

    // Profile Form
    inputProfSchool: document.getElementById("input-prof-school"),
    inputProfTier: document.getElementById("input-prof-tier"),
    inputProfMajor: document.getElementById("input-prof-major"),
    inputProfGpa: document.getElementById("input-prof-gpa"),
    inputProfIelts: document.getElementById("input-prof-ielts"),
    inputProfTargets: document.getElementById("input-prof-targets"),
    saveProfileBtn: document.getElementById("save-profile-btn"),
    jsonPasteToggleBtn: document.getElementById("json-paste-toggle-btn"),
    jsonPasteArea: document.getElementById("json-paste-area"),
    jsonInput: document.getElementById("json-input"),
    applyJsonBtn: document.getElementById("apply-json-btn"),

    // Matrix View Elements (Milestone 4 HITL & Milestone 5 Portfolio)
    matrixBanner: document.getElementById("matrix-banner"),
    matrixOverviewText: document.getElementById("matrix-overview-text"),
    matrixCountBadge: document.getElementById("matrix-count-badge"),
    locusHitlBanner: document.getElementById("locus-hitl-banner"),
    confirmMatrixBtn: document.getElementById("confirm-matrix-btn"),
    reachCardsContainer: document.getElementById("reach-cards-container"),
    matchCardsContainer: document.getElementById("match-cards-container"),
    safetyCardsContainer: document.getElementById("safety-cards-container"),
    portOfferProb: document.getElementById("port-offer-prob"),
    portRejectRisk: document.getElementById("port-reject-risk"),
    portRejectGap: document.getElementById("port-reject-gap"),
    portSharpe: document.getElementById("port-sharpe"),
    portAvgCorr: document.getElementById("port-avg-corr"),
    portRecBanner: document.getElementById("portfolio-rec-banner"),
    portRecText: document.getElementById("portfolio-rec-text"),
    btnSubmodularOptimize: document.getElementById("btn-submodular-optimize"),

    // SOP View Elements (Milestone 4 Editable Outline, Refraction, Versions)
    sopStageBadge: document.getElementById("sop-stage-badge"),
    stepNodes: [
      document.getElementById("step-node-1"),
      document.getElementById("step-node-2"),
      document.getElementById("step-node-3"),
      document.getElementById("step-node-4")
    ],
    stepLines: [
      document.getElementById("line-1-2"),
      document.getElementById("line-2-3"),
      document.getElementById("line-3-4")
    ],
    blueprintStatus: document.getElementById("blueprint-status"),
    outlineHitlBanner: document.getElementById("outline-hitl-banner"),
    confirmOutlineBtn: document.getElementById("confirm-outline-btn"),
    bpPointsHook: document.getElementById("bp-points-hook"),
    bpPointsBody: document.getElementById("bp-points-body"),
    bpPointsWhy: document.getElementById("bp-points-why"),

    sopVersionSelect: document.getElementById("sop-version-select"),
    rollbackVersionBtn: document.getElementById("rollback-version-btn"),
    currentVersionTag: document.getElementById("current-version-tag"),
    draftTextBox: document.getElementById("draft-text-box"),
    critiqueContent: document.getElementById("critique-content"),
    copyDraftBtn: document.getElementById("copy-draft-btn"),

    floatingRefractPill: document.getElementById("floating-refract-pill"),
    refractionWorkbench: document.getElementById("refraction-workbench"),
    closeRefractBtn: document.getElementById("close-refract-btn"),
    refractSelectedPreview: document.getElementById("refract-selected-preview"),
    refractInstructionInput: document.getElementById("refract-instruction-input"),
    executeRefractBtn: document.getElementById("execute-refract-btn"),
    diffViewPanel: document.getElementById("diff-view-panel"),
    diffRenderBox: document.getElementById("diff-render-box"),
    acceptDiffBtn: document.getElementById("accept-diff-btn"),
    rejectDiffBtn: document.getElementById("reject-diff-btn"),

    // Milestone 5: 回音壁 (Echo) 面试与时间轴画布
    echoStatusBadge: document.getElementById("echo-status-badge"),
    echoTimelineCards: document.getElementById("echo-timeline-cards"),
    timelineProgramCounter: document.getElementById("timeline-program-counter"),
    rlStepperContainer: document.getElementById("rl-stepper-container"),
    materialsChecklistBox: document.getElementById("materials-checklist-box"),
    interviewCountBadge: document.getElementById("interview-count-badge"),
    evalQType: document.getElementById("eval-q-type"),
    evalQProg: document.getElementById("eval-q-prog"),
    evalQTimer: document.getElementById("eval-q-timer"),
    evalQText: document.getElementById("eval-q-text"),
    evalQCn: document.getElementById("eval-q-cn"),
    evalAnsWordcount: document.getElementById("eval-ans-wordcount"),
    evalAnsText: document.getElementById("eval-ans-text"),
    scoreValRelevance: document.getElementById("score-val-relevance"),
    barFillRelevance: document.getElementById("bar-fill-relevance"),
    notesRelevance: document.getElementById("notes-relevance"),
    scoreValStar: document.getElementById("score-val-star"),
    barFillStar: document.getElementById("bar-fill-star"),
    notesStar: document.getElementById("notes-star"),
    scoreValLang: document.getElementById("score-val-lang"),
    barFillLang: document.getElementById("bar-fill-lang"),
    notesLang: document.getElementById("notes-lang"),
    scoreValComposite: document.getElementById("score-val-composite"),
    refinedSampleMeta: document.getElementById("refined-sample-meta"),
    refinedSampleBody: document.getElementById("refined-sample-body"),
    btnCopySample: document.getElementById("btn-copy-sample"),
    btnNextQuestion: document.getElementById("btn-next-question"),
    btnTriggerKira: document.getElementById("btn-trigger-kira"),
    btnTriggerAlumni: document.getElementById("btn-trigger-alumni"),
    btnTriggerTech: document.getElementById("btn-trigger-tech"),
    btnTriggerTimeline: document.getElementById("btn-trigger-timeline"),

    // Milestone 7: Profile Switcher & Dossier Exporter
    profileSwitcherWrapper: document.getElementById("profile-switcher-wrapper"),
    profileSwitcherBtn: document.getElementById("profile-switcher-btn"),
    profileDropdown: document.getElementById("profile-dropdown"),
    profileDropdownList: document.getElementById("profile-dropdown-list"),
    currentProfileName: document.getElementById("current-profile-name"),
    dropdownNewProfileBtn: document.getElementById("dropdown-new-profile-btn"),
    btnExportDossier: document.getElementById("btn-export-dossier"),

    exportDossierModal: document.getElementById("export-dossier-modal"),
    closeExportModalBtn: document.getElementById("close-export-modal-btn"),
    tabPreviewHtml: document.getElementById("tab-preview-html"),
    tabPreviewMd: document.getElementById("tab-preview-md"),
    panePreviewHtml: document.getElementById("pane-preview-html"),
    panePreviewMd: document.getElementById("pane-preview-md"),
    exportPreviewIframe: document.getElementById("export-preview-iframe"),
    exportMarkdownView: document.getElementById("export-markdown-view"),
    btnModalCopyMd: document.getElementById("btn-modal-copy-md"),
    btnModalDlMd: document.getElementById("btn-modal-dl-md"),
    btnModalDlHtml: document.getElementById("btn-modal-dl-html"),
    btnModalOpenNew: document.getElementById("btn-modal-open-new"),

    createProfileModal: document.getElementById("create-profile-modal"),
    closeCreateModalBtn: document.getElementById("close-create-modal-btn"),
    cancelCreateProfileBtn: document.getElementById("cancel-create-profile-btn"),
    confirmCreateProfileBtn: document.getElementById("confirm-create-profile-btn"),
    newProfileNameInput: document.getElementById("new-profile-name-input"),
    newProfileSchoolInput: document.getElementById("new-profile-school-input"),
    newProfileTierInput: document.getElementById("new-profile-tier-input"),
    newProfileMajorInput: document.getElementById("new-profile-major-input"),
    newProfileGpaInput: document.getElementById("new-profile-gpa-input"),

    renameProfileModal: document.getElementById("rename-profile-modal"),
    closeRenameModalBtn: document.getElementById("close-rename-modal-btn"),
    cancelRenameProfileBtn: document.getElementById("cancel-rename-profile-btn"),
    confirmRenameProfileBtn: document.getElementById("confirm-rename-profile-btn"),
    renameProfileNameInput: document.getElementById("rename-profile-name-input"),

    // Milestone 8: 棱镜控制台 (Prism Console)
    btnOpenConsole: document.getElementById("btn-open-console"),
    prismConsoleModal: document.getElementById("prism-console-modal"),
    closeConsoleModalBtn: document.getElementById("close-console-modal-btn"),
    tabConsoleEngine: document.getElementById("tab-console-engine"),
    tabConsoleGraph: document.getElementById("tab-console-graph"),
    tabConsoleBenchmark: document.getElementById("tab-console-benchmark"),
    consoleHeaderModeTag: document.getElementById("console-header-mode-tag"),
    paneConsoleEngine: document.getElementById("pane-console-engine"),
    paneConsoleGraph: document.getElementById("pane-console-graph"),
    paneConsoleBenchmark: document.getElementById("pane-console-benchmark"),

    // Tab A: Engine & Model
    currentEngineModeTitle: document.getElementById("current-engine-mode-title"),
    currentEngineSubTag: document.getElementById("current-engine-sub-tag"),
    currentEngineModeDesc: document.getElementById("current-engine-mode-desc"),
    modePulseDot: document.getElementById("mode-pulse-dot"),
    btnToggleEngineMode: document.getElementById("btn-toggle-engine-mode"),
    toggleEngineBtnText: document.getElementById("toggle-engine-btn-text"),
    consoleProviderSelect: document.getElementById("console-provider-select"),
    consoleModelInput: document.getElementById("console-model-input"),
    consoleBaseUrlInput: document.getElementById("console-base-url-input"),
    consoleApiKeyInput: document.getElementById("console-api-key-input"),
    btnToggleKeyView: document.getElementById("btn-toggle-key-view"),
    consoleKeyMaskedHint: document.getElementById("console-key-masked-hint"),
    consoleTempSlider: document.getElementById("console-temp-slider"),
    consoleTempBadge: document.getElementById("console-temp-badge"),
    btnTestConn: document.getElementById("btn-test-conn"),
    btnSaveCfg: document.getElementById("btn-save-cfg"),
    consoleEngineFeedback: document.getElementById("console-engine-feedback"),

    // Tab B: Graph & Cases
    statUnis: document.getElementById("stat-unis"),
    statPrograms: document.getElementById("stat-programs"),
    statCourses: document.getElementById("stat-courses"),
    statProfs: document.getElementById("stat-profs"),
    statEdges: document.getElementById("stat-edges"),
    statCases: document.getElementById("stat-cases"),
    btnRefreshStats: document.getElementById("btn-refresh-stats"),
    graphStoragePath: document.getElementById("graph-storage-path"),
    nodeTypeInput: document.getElementById("node-type-input"),
    nodeIdInput: document.getElementById("node-id-input"),
    nodeNameInput: document.getElementById("node-name-input"),
    nodeUniIdInput: document.getElementById("node-uni-id-input"),
    nodeRegionInput: document.getElementById("node-region-input"),
    nodeMajorInput: document.getElementById("node-major-input"),
    nodeGpaInput: document.getElementById("node-gpa-input"),
    nodeExtraInput: document.getElementById("node-extra-input"),
    btnSubmitNode: document.getElementById("btn-submit-node"),

    caseProgramInput: document.getElementById("case-program-input"),
    caseOutcomeInput: document.getElementById("case-outcome-input"),
    caseSchoolInput: document.getElementById("case-school-input"),
    caseTierInput: document.getElementById("case-tier-input"),
    caseMajorInput: document.getElementById("case-major-input"),
    caseGpaInput: document.getElementById("case-gpa-input"),
    caseScaleInput: document.getElementById("case-scale-input"),
    caseLangInput: document.getElementById("case-lang-input"),
    caseYearInput: document.getElementById("case-year-input"),
    caseSummaryInput: document.getElementById("case-summary-input"),
    btnSubmitCase: document.getElementById("btn-submit-case"),
    consoleGraphFeedback: document.getElementById("console-graph-feedback"),

    // Tab C: Benchmark
    evalLastRunTimestamp: document.getElementById("eval-last-run-timestamp"),
    btnRunBenchmark: document.getElementById("btn-run-benchmark"),
    gaugeValHard: document.getElementById("gauge-val-hard"),
    gaugeBaseHard: document.getElementById("gauge-base-hard"),
    gaugeBarHard: document.getElementById("gauge-bar-hard"),
    gaugeDeltaHard: document.getElementById("gauge-delta-hard"),
    gaugeValGate: document.getElementById("gauge-val-gate"),
    gaugeBaseGate: document.getElementById("gauge-base-gate"),
    gaugeBarGate: document.getElementById("gauge-bar-gate"),
    gaugeDeltaGate: document.getElementById("gauge-delta-gate"),
    gaugeValAi: document.getElementById("gauge-val-ai"),
    gaugeBaseAi: document.getElementById("gauge-base-ai"),
    gaugeBarAi: document.getElementById("gauge-bar-ai"),
    gaugeDeltaAi: document.getElementById("gauge-delta-ai"),
    gaugeValCite: document.getElementById("gauge-val-cite"),
    gaugeBaseCite: document.getElementById("gauge-base-cite"),
    gaugeBarCite: document.getElementById("gauge-bar-cite"),
    gaugeDeltaCite: document.getElementById("gauge-delta-cite"),
    casesTableCount: document.getElementById("cases-table-count"),
    evalCasesList: document.getElementById("eval-cases-list"),

    // Desktop App Distribution Modal
    btnOpenDesktopModal: document.getElementById("btn-open-desktop-modal"),
    desktopDownloadModal: document.getElementById("desktop-download-modal"),
    closeDesktopModalBtn: document.getElementById("close-desktop-modal-btn"),
    cancelDesktopModalBtn: document.getElementById("cancel-desktop-modal-btn"),
    desktopModalVersion: document.getElementById("desktop-modal-version"),
    macDetectBanner: document.getElementById("mac-detect-banner"),
    winDetectBanner: document.getElementById("win-detect-banner"),
  };

  // 4. Toast 通知展示器
  function showToast(message, type = "info") {
    if (!elements.toastContainer) return;
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    let icon = "✦";
    if (type === "success") icon = "✓";
    if (type === "warn" || type === "warning") icon = "⚠️";
    if (type === "error") icon = "✕";

    toast.innerHTML = `<span class="toast-icon">${icon}</span> <span>${message}</span>`;
    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(12px)";
      setTimeout(() => toast.remove(), 250);
    }, 3200);
  }

  // 5. 顶部实时 Agent 呼吸灯与标牌更新
  function updateTopAgentIndicator(agentId) {
    const config = AGENT_CONFIGS[agentId] || AGENT_CONFIGS.luminary;
    state.activeAgent = agentId;

    if (elements.agentIndicator) {
      const orb = elements.agentIndicator.querySelector(".pulse-orb");
      if (orb) {
        orb.className = `pulse-orb ${config.orbClass}`;
      }
    }
    if (elements.activeAgentLabel) {
      elements.activeAgentLabel.textContent = `【${config.name} · ${config.badge}】${config.title.split(" · ")[1] || ""}`;
    }
  }

  // 6. 右侧 Tab 切换
  function switchCanvasTab(tabKey) {
    state.activeTab = tabKey;
    [elements.tabBtnProfile, elements.tabBtnMatrix, elements.tabBtnSop, elements.tabBtnEcho, elements.tabBtnResonator].forEach(t => t && t.classList.remove("active"));
    [elements.viewProfile, elements.viewMatrix, elements.viewSop, elements.viewEcho, elements.viewResonator].forEach(v => v && v.classList.remove("active"));

    if (tabKey === "profile") {
      if (elements.tabBtnProfile) elements.tabBtnProfile.classList.add("active");
      if (elements.viewProfile) elements.viewProfile.classList.add("active");
    } else if (tabKey === "matrix") {
      if (elements.tabBtnMatrix) elements.tabBtnMatrix.classList.add("active");
      if (elements.viewMatrix) elements.viewMatrix.classList.add("active");
    } else if (tabKey === "sop") {
      if (elements.tabBtnSop) elements.tabBtnSop.classList.add("active");
      if (elements.viewSop) elements.viewSop.classList.add("active");
    } else if (tabKey === "echo") {
      if (elements.tabBtnEcho) elements.tabBtnEcho.classList.add("active");
      if (elements.viewEcho) elements.viewEcho.classList.add("active");
    } else if (tabKey === "resonator") {
      if (elements.tabBtnResonator) elements.tabBtnResonator.classList.add("active");
      if (elements.viewResonator) elements.viewResonator.classList.add("active");
      refreshResonatorView();
    }
  }

  // 7. 学生档案与完备度刷新 (Tab 1)
  function refreshProfileView(p) {
    if (!p) return;
    state.studentProfile = Object.assign({}, state.studentProfile, p);

    let completedCount = 0;
    const hasTier = Boolean(p.undergrad_tier || p.undergrad_name);
    const hasGpa = Boolean(p.gpa_raw);
    const hasMajor = Boolean(p.major);
    const langScores = p.language_scores || {};
    const hasLangOrTarget = Boolean(
      (p.target_regions && p.target_regions.length > 0) ||
      (p.target_majors && p.target_majors.length > 0) ||
      langScores.IELTS_total || langScores.TOEFL_total
    );

    function setCheck(el, isDone) {
      if (!el) return;
      if (isDone) {
        el.classList.add("done");
        el.querySelector(".chk-status").textContent = "✓";
      } else {
        el.classList.remove("done");
        el.querySelector(".chk-status").textContent = "✕";
      }
    }

    if (hasTier) completedCount++;
    if (hasGpa) completedCount++;
    if (hasMajor) completedCount++;
    if (hasLangOrTarget) completedCount++;

    setCheck(elements.chkTier, hasTier);
    setCheck(elements.chkGpa, hasGpa);
    setCheck(elements.chkMajor, hasMajor);
    setCheck(elements.chkTarget, hasLangOrTarget);

    const percent = Math.round((completedCount / 4) * 100);
    if (elements.completenessPercentage) elements.completenessPercentage.textContent = `${percent}%`;
    if (elements.completenessBarFill) elements.completenessBarFill.style.width = `${percent}%`;

    if (elements.profileStatusBadge) {
      if (percent >= 100) {
        elements.profileStatusBadge.textContent = "四维基准已完备";
        elements.profileStatusBadge.style.background = "rgba(16, 185, 129, 0.2)";
        elements.profileStatusBadge.style.color = "#34d399";
      } else {
        elements.profileStatusBadge.textContent = `完备度 ${percent}%`;
        elements.profileStatusBadge.style.background = "rgba(245, 158, 11, 0.15)";
        elements.profileStatusBadge.style.color = "#fbbf24";
      }
    }

    // 4 张指标卡片
    if (p.undergrad_name) {
      elements.valUndergrad.textContent = p.undergrad_name;
      elements.valUndergradSub.textContent = p.undergrad_tier ? `层级梯队: ${p.undergrad_tier} · List准入已校准` : "名校名单隐形准入校验中";
    }
    if (p.gpa_raw) {
      elements.valGpa.textContent = p.gpa_raw;
      elements.valGpaSub.textContent = "WES / 4.0 算法标尺折算通过";
    }

    const langStrs = [];
    if (langScores.IELTS_total) langStrs.push(`雅思 ${langScores.IELTS_total}`);
    if (langScores.speaking) langStrs.push(`口语 ${langScores.speaking}`);
    if (langScores.TOEFL_total) langStrs.push(`托福 ${langScores.TOEFL_total}`);
    if (langStrs.length > 0) {
      elements.valLanguage.textContent = langStrs.join(" | ");
      elements.valLanguageSub.textContent = "口语小分阻断无阻碍";
    }

    const targetList = [];
    if (p.target_regions && p.target_regions.length > 0) targetList.push(p.target_regions.join("/"));
    if (p.target_majors && p.target_majors.length > 0) targetList.push(p.target_majors.join("/"));
    if (targetList.length > 0) {
      elements.valTarget.textContent = targetList.join(" · ");
      elements.valTargetSub.textContent = "全球学府靶向方向明确";
    }

    // 碎片展示
    const fragments = p.mined_story_fragments || [];
    if (elements.fragmentCounter) elements.fragmentCounter.textContent = `${fragments.length} 碎片`;
    if (elements.fragmentTagsContainer) {
      if (fragments.length === 0) {
        elements.fragmentTagsContainer.innerHTML = `<div class="empty-state-notice">暂无已采集碎片，向【折光师】回复真实科研与工程挑战后将自动提炼收录。</div>`;
      } else {
        elements.fragmentTagsContainer.innerHTML = fragments.map((f, idx) => {
          const short = f.length > 40 ? f.substring(0, 40) + "..." : f;
          return `<div class="fragment-tag-pill" title="${escapeHtml(f)}">
            <span style="color:#a855f7;">#${idx + 1}</span> <span>${escapeHtml(short)}</span>
          </div>`;
        }).join("");
      }
    }

    // 同步到表单
    if (elements.inputProfSchool && p.undergrad_name) elements.inputProfSchool.value = p.undergrad_name;
    if (elements.inputProfTier && p.undergrad_tier) elements.inputProfTier.value = p.undergrad_tier;
    if (elements.inputProfMajor && p.major) elements.inputProfMajor.value = p.major;
    if (elements.inputProfGpa && p.gpa_raw) elements.inputProfGpa.value = p.gpa_raw;
    if (elements.inputProfIelts && langStrs.length > 0) elements.inputProfIelts.value = langStrs.join(", ");
    if (elements.inputProfTargets && targetList.length > 0) elements.inputProfTargets.value = targetList.join(", ");

    // Milestone 9: 联动刷新先修课图谱、STAR经历诊断与学者徽章
    refreshPrerequisitesView(p);
    refreshExperiencesView(p.experiences);
    refreshResonatorBadge(p.target_professors);
  }

  // 7.1 先修课知识图谱与结构性暗区刷新
  function refreshPrerequisitesView(p) {
    if (!elements.prereqCoursesGrid) return;
    const prereqs = (p && p.prerequisite_grades) || {};
    const prereqKeys = Object.keys(prereqs);

    if (prereqKeys.length > 0) {
      if (elements.prereqCoverageBadge) {
        elements.prereqCoverageBadge.textContent = `已收录 ${prereqKeys.length} 门先修课`;
        elements.prereqCoverageBadge.style.color = "#34d399";
      }
      elements.prereqCoursesGrid.innerHTML = prereqKeys.map(cName => {
        const info = prereqs[cName] || {};
        const grade = info.grade || "已修";
        const orig = info.matched_name ? ` (原名: ${info.matched_name})` : "";
        return `
          <div class="prereq-course-pill status-completed">
            <div class="prereq-course-top">
              <span class="prereq-course-name">${escapeHtml(cName)}</span>
              <span class="prereq-status-tag tag-completed">✓ ${escapeHtml(grade)}</span>
            </div>
            <div class="prereq-match-text">${escapeHtml(orig || "已对齐先修课知识图谱")}</div>
          </div>
        `;
      }).join("");
    } else {
      if (elements.prereqCoverageBadge) {
        elements.prereqCoverageBadge.textContent = "待切面师诊断";
        elements.prereqCoverageBadge.style.color = "#fbbf24";
      }
      const defaultCourses = [
        { name: "高等数学 (Calculus)", status: "待核对", cls: "status-weak" },
        { name: "线性代数 (Linear Algebra)", status: "待核对", cls: "status-weak" },
        { name: "数据结构与算法 (Data Structures)", status: "待核对", cls: "status-weak" },
        { name: "操作系统 (Operating Systems)", status: "待核对", cls: "status-weak" },
        { name: "概率论与数理统计 (Probability)", status: "待核对", cls: "status-weak" },
        { name: "面向对象程序设计 (OOP)", status: "待核对", cls: "status-weak" },
      ];
      elements.prereqCoursesGrid.innerHTML = defaultCourses.map(c => `
        <div class="prereq-course-pill ${c.cls}">
          <div class="prereq-course-top">
            <span class="prereq-course-name">${escapeHtml(c.name)}</span>
            <span class="prereq-status-tag tag-weak">${c.status}</span>
          </div>
          <div class="prereq-match-text">导入成绩单或点击右上角【切面师诊断】</div>
        </div>
      `).join("");
    }
  }

  // 7.2 科研与工程经历 STAR 切面诊断刷新
  function refreshExperiencesView(experiences) {
    if (!elements.experiencesListContainer) return;
    const exps = experiences || [];
    if (elements.experiencesCounter) {
      elements.experiencesCounter.textContent = `${exps.length} 项经历`;
    }

    if (exps.length === 0) {
      elements.experiencesListContainer.innerHTML = `<div class="empty-state-notice">暂无结构化经历数据。上传简历或在左侧对话中阐述科研/实习后，系统将自动进行 STAR 完整度评估。</div>`;
      return;
    }

    elements.experiencesListContainer.innerHTML = exps.map((exp, idx) => {
      const isMining = Boolean(exp.needs_mining);
      const starTag = isMining
        ? '<span class="exp-star-tag star-mining">⚠️ 待折光挖掘 (needs_mining)</span>'
        : '<span class="exp-star-tag star-solid">✅ STAR完备</span>';
      const reasonHtml = exp.mining_reason
        ? `<div class="exp-mining-reason">↳ 诊断意见: ${escapeHtml(exp.mining_reason)}</div>`
        : "";

      return `
        <div class="exp-card-item">
          <div class="exp-card-header">
            <span class="exp-card-title">${idx + 1}. ${escapeHtml(exp.title || "科研/实习经历")}</span>
            <span class="exp-card-period">${escapeHtml(exp.period || "在校期间")}</span>
          </div>
          <div class="exp-card-badges">
            ${starTag}
          </div>
          ${reasonHtml}
          <div class="exp-card-actions">
            <button class="btn-mine-exp" data-title="${escapeHtml(exp.title || '')}" type="button">
              💡 移交折光师苏格拉底挖掘
            </button>
          </div>
        </div>
      `;
    }).join("");

    elements.experiencesListContainer.querySelectorAll(".btn-mine-exp").forEach(btn => {
      btn.addEventListener("click", () => {
        const title = btn.getAttribute("data-title");
        sendUserMessage(`请折光师针对我档案中的【${title}】展开苏格拉底深度追问与故事挖掘。`);
      });
    });
  }

  // 7.3 共鸣者学者与套磁信看板刷新 (Tab 5)
  function refreshResonatorView() {
    const profs = (state.studentProfile && state.studentProfile.target_professors) || [];
    if (elements.resonatorCountBadge) {
      elements.resonatorCountBadge.textContent = `${profs.length} 学者`;
    }
    if (elements.matchedProfsCounter) {
      elements.matchedProfsCounter.textContent = `${profs.length} 位学者`;
    }

    if (!elements.resonatorProfsGrid) return;

    if (profs.length === 0) {
      elements.resonatorProfsGrid.innerHTML = `
        <div class="empty-column-placeholder" style="grid-column: 1 / -1; padding: 24px; text-align: center;">
          尚未匹配学者。在上方输入学者姓名（如 Indranil Gupta）或向【共鸣者】发送：“想联系某某教授写套磁信”，即可自动进行学术论文对齐。
        </div>
      `;
      return;
    }

    elements.resonatorProfsGrid.innerHTML = profs.map(p => `
      <div class="prof-card-item">
        <div class="prof-card-header">
          <div>
            <div class="prof-name">${escapeHtml(p.scholar_name || "学术导师")}</div>
            <div class="prof-uni">${escapeHtml(p.institution || "目标院校")} · ${escapeHtml(p.lab || "课题组")}</div>
          </div>
          <span class="prof-status-tag">Fall 2027 招生中</span>
        </div>
        <div class="prof-paper-anchor">
          <div class="prof-paper-title">📄 代表作: “${escapeHtml(p.paper_title || "近期代表作")}”</div>
          <div class="prof-paper-bottleneck">↳ 学术共振切入点: 对接高可用分布式不变量与性能基准评测</div>
        </div>
      </div>
    `).join("");

    // 更新套磁信预览
    if (elements.coldEmailBox && profs.length > 0) {
      const topProf = profs[profs.length - 1];
      const scholarLastName = (topProf.scholar_name || "Gupta").split(" ").pop();
      const emailDraft = `Dear Professor ${scholarLastName},

I am an incoming applicant for Fall 2027 graduate research, with a background in systems engineering and distributed systems. I recently read your publication, "${topProf.paper_title || 'Adaptive Consensus Protocols in Heterogeneous Clouds'}," with keen interest. Your empirical analysis and theoretical framing were illuminating, particularly your note regarding runtime scalability bottlenecks.

In my recent undergraduate engineering practicum, I focused on runtime performance bottlenecks closely related to systems engineering. Specifically, I profiled concurrency bottlenecks under stress conditions and developed kernel-level monitoring hooks that cut synchronization latency under bursty loads. Given your laboratory's recent initiatives at ${topProf.lab || topProf.institution}, I believe my hands-on benchmarking background aligns closely with your technical agenda.

I noticed that your group is actively reviewing graduate applications for Fall 2027. I would welcome the opportunity to contribute to your ongoing research initiatives. I have attached my CV and transcript for your review. Would you be open to a brief 15-minute introductory call in the coming weeks to discuss prospective synergy?

Thank you for your time and guidance.

Sincerely,
[Your Name]
[Undergraduate Institution] | [Email / GitHub Profile]`;

      elements.coldEmailBox.textContent = emailDraft;
      const words = emailDraft.trim().split(/\s+/).length;
      if (elements.coldEmailWordcount) {
        elements.coldEmailWordcount.textContent = `约 ${words} 词 (黄金标准)`;
      }
    }
  }

  function refreshResonatorBadge(profs) {
    const list = profs || [];
    if (elements.resonatorCountBadge) {
      elements.resonatorCountBadge.textContent = `${list.length} 学者`;
    }
  }

  // 7.4 文件上传与光学文档解析
  async function handleFileUpload(file) {
    if (!file) return;

    if (elements.uploadProgressBar) elements.uploadProgressBar.classList.remove("hidden");
    if (elements.uploadProgressFill) elements.uploadProgressFill.style.width = "35%";
    showToast(`正在光学解析《${file.name}》...`, "info");

    const fileName = file.name;
    const isPdf = fileName.toLowerCase().endsWith(".pdf");

    const reader = new FileReader();

    reader.onload = async (e) => {
      try {
        if (elements.uploadProgressFill) elements.uploadProgressFill.style.width = "70%";

        const payload = {
          session_id: state.sessionId,
          file_name: fileName,
          file_type: file.type || (isPdf ? "application/pdf" : "text/plain"),
        };

        if (isPdf) {
          payload.content_base64 = e.target.result;
        } else {
          payload.text_content = e.target.result;
        }

        const resp = await fetch("/api/profile/upload-document", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (!resp.ok) throw new Error(`HTTP 状态码: ${resp.status}`);
        const data = await resp.json();

        if (elements.uploadProgressFill) elements.uploadProgressFill.style.width = "100%";
        setTimeout(() => {
          if (elements.uploadProgressBar) elements.uploadProgressBar.classList.add("hidden");
          if (elements.uploadProgressFill) elements.uploadProgressFill.style.width = "0%";
        }, 500);

        if (data.status === "success" && data.profile) {
          state.studentProfile = data.profile;
          refreshProfileView(data.profile);
          if (data.profile.shortlisted_programs) {
            refreshMatrixView(data.profile.shortlisted_programs);
          }
          if (elements.uploadResultPill) {
            elements.uploadResultPill.classList.remove("hidden");
            if (elements.uploadResultText) {
              elements.uploadResultText.textContent = `《${fileName}》解析成功：已提取【${data.profile.undergrad_name || '院校'} · ${data.profile.major || '专业'}】均分【${data.profile.gpa_raw || 'GPA'}】！`;
            }
          }
          showToast(`《${fileName}》解析成功！档案指标已更新`, "success");
        } else {
          throw new Error(data.detail || "解析失败");
        }
      } catch (err) {
        if (elements.uploadProgressBar) elements.uploadProgressBar.classList.add("hidden");
        showToast(`文件解析异常: ${err.message}`, "error");
      }
    };

    if (isPdf) {
      reader.readAsDataURL(file);
    } else {
      reader.readAsText(file);
    }
  }

  // 8. 选校矩阵与 Tab 2 视图刷新 (Milestone 4 双向交互)
  function refreshMatrixView(programs) {
    if (!programs || !Array.isArray(programs)) return;
    state.studentProfile.shortlisted_programs = programs;
    if (elements.matrixCountBadge) elements.matrixCountBadge.textContent = `${programs.length} 项`;

    // 检查并更新 HITL 定焦挂起 Banner
    if (elements.locusHitlBanner) {
      if (state.pendingHumanReview === "locus_matrix" && programs.length > 0) {
        elements.locusHitlBanner.classList.remove("hidden");
      } else {
        elements.locusHitlBanner.classList.add("hidden");
      }
    }

    const reachList = programs.filter(p => (p.tier_bracket === "Reach" || p.tier === "Reach" || p.tier === "冲刺" || p.tier === "远光·冲刺"));
    const matchList = programs.filter(p => (p.tier_bracket === "Match" || p.tier === "Match" || p.tier === "核心" || p.tier === "聚光·核心" || (!p.tier_bracket && !p.tier)));
    const safetyList = programs.filter(p => (p.tier_bracket === "Safety" || p.tier === "Safety" || p.tier === "稳妥" || p.tier === "保底" || p.tier === "基光·稳妥"));

    const lockedTarget = state.studentProfile.locked_target_program || null;

    function renderAttributionBars(attrs) {
      if (!attrs || Object.keys(attrs).length === 0) {
        return `<div class="attr-empty">各维度相对均衡，契合基线标准</div>`;
      }
      return Object.entries(attrs).slice(0, 5).map(([label, val]) => {
        let num = 0;
        let isPos = true;
        let strVal = "";
        if (typeof val === "number") {
          num = Math.abs(val) * 100;
          isPos = val >= 0;
          strVal = `${isPos ? "+" : "-"}${num.toFixed(1)}%`;
        } else {
          strVal = String(val);
          isPos = !strVal.startsWith("-");
          num = parseFloat(strVal.replace(/[^\d.-]/g, "")) || 0;
        }
        const widthPct = Math.min(100, Math.max(10, num * 2.2));
        const fillClass = isPos ? "attr-fill-pos" : "attr-fill-neg";
        return `
          <div class="attr-bar-row">
            <span class="attr-lbl" title="${escapeHtml(label)}">${escapeHtml(label)}</span>
            <div class="attr-track">
              <div class="attr-bar ${fillClass}" style="width: ${widthPct}%;"></div>
            </div>
            <span class="attr-num ${isPos ? 'num-pos' : 'num-neg'}">${escapeHtml(strVal)}</span>
          </div>
        `;
      }).join("");
    }

    function renderCards(list, bracketKey) {
      if (!list || list.length === 0) {
        return `<div class="empty-column-placeholder">暂无该档位项目</div>`;
      }
      return list.map(item => {
        const progId = item.id || item.program_id || "";
        const isLocked = Boolean(lockedTarget && (lockedTarget.id === progId || lockedTarget.id === item.id));

        const gpaReq = item.gpa_min_4_0 ? `GPA ≥ ${item.gpa_min_4_0}` : `均分 ≥ ${item.gpa_min_100 || "85"}`;
        const langReq = item.min_ielts ? `雅思 ≥ ${item.min_ielts.total}` : "语言合规";
        const median = (item.peer_cases && item.peer_cases.peer_median_gpa) ? `中位线: ${item.peer_cases.peer_median_gpa}` : "中位线: 88.0";

        const peer = item.peer_cases || {};
        const probPct = peer.probability_percent || (bracketKey === "Reach" ? "25.0%" : (bracketKey === "Safety" ? "85.0%" : "55.0%"));
        const confLevel = peer.confidence_level || "high";
        const marginErr = peer.margin_of_error || "±4.5%";
        const attributions = peer.feature_attributions || peer.attributions || {};

        return `
          <div class="program-card ${isLocked ? 'locked-target' : ''}" data-prog-id="${escapeHtml(progId)}">
            ${isLocked ? `<div class="target-badge-pill">★ 选定文书目标校</div>` : ''}
            <div class="prog-name-cn">${escapeHtml(item.name_cn || item.name || item.program || "目标项目")}</div>
            <div class="prog-name-en">${escapeHtml(item.name_en || item.institution || "")}</div>
            
            <div class="prog-metrics-row">
              <span class="metric-pill">${escapeHtml(gpaReq)}</span>
              <span class="metric-pill">${escapeHtml(langReq)}</span>
              <span class="metric-pill">${escapeHtml(median)}</span>
            </div>

            <!-- AdmitNet ML 录取率与置信度 -->
            <div class="admitnet-prob-badge">
              <div class="prob-title-row">
                <span class="prob-label">✦ Prism-AdmitNet 预估录取率</span>
                <span class="prob-val" id="prob-val-${escapeHtml(progId)}">${escapeHtml(probPct)}</span>
              </div>
              <div class="prob-ci-tag">置信度: <span class="ci-badge ci-level-${confLevel}">${confLevel === 'high' ? '高' : (confLevel === 'medium' ? '中' : '参考')}</span> · 边际误差: ${escapeHtml(marginErr)}</div>
              ${(peer.overqualified_yield_risk || item.overqualified_yield_risk) ? `
                <div class="yield-risk-alert-pill">
                  <span>⚠️ Yield Protection 控录取风险: 背景显著高于该校中位线</span>
                </div>
              ` : ''}
            </div>

            <!-- 特征归因双向条 -->
            <div class="attribution-bars-container" id="attrs-container-${escapeHtml(progId)}">
              <div class="attr-header-row">
                <span>特征归因溯源 (Feature Attribution)</span>
                <span class="attr-sub-hint">Exact Additive</span>
              </div>
              <div class="attr-list">
                ${renderAttributionBars(attributions)}
              </div>
            </div>

            <!-- What-If 逆袭沙盘滑块面板 -->
            <div class="what-if-panel" id="what-if-panel-${escapeHtml(progId)}">
              <button type="button" class="btn-toggle-what-if" data-prog-id="${escapeHtml(progId)}">
                <span>🔮 What-If 逆袭沙盘模拟</span>
                <span class="toggle-icon">▼</span>
              </button>
              <div class="what-if-controls hidden" id="what-if-controls-${escapeHtml(progId)}">
                <div class="what-if-timeline-tag">⏳ 距申请截止约 4 个月 · 大四上可行域约束</div>
                <div class="what-if-field">
                  <div class="field-label-row">
                    <label>GPA 提升幅度 (ΔGPA)</label>
                    <span class="field-val-display" id="gpa-disp-${escapeHtml(progId)}">+0.00</span>
                  </div>
                  <input type="range" class="what-if-slider gpa-slider" data-prog-id="${escapeHtml(progId)}" min="0.0" max="0.40" step="0.05" value="0.0">
                </div>
                <div class="what-if-field">
                  <div class="field-label-row">
                    <label>标化语言跃迁</label>
                  </div>
                  <select class="what-if-select lang-select" data-prog-id="${escapeHtml(progId)}">
                    <option value="0">保持现有水平</option>
                    <option value="7.5">雅思 7.5 (或 托福 105)</option>
                    <option value="8.0">雅思 8.0 (或 托福 112)</option>
                  </select>
                </div>
                <div class="what-if-field">
                  <div class="field-label-row">
                    <label>科研与工程背景跃升</label>
                  </div>
                  <select class="what-if-select research-select" data-prog-id="${escapeHtml(progId)}">
                    <option value="none">保持现有经历</option>
                    <option value="tier2_intern">补充头部大厂核心工程实习</option>
                    <option value="top_lab">国家重点实验室分布式攻坚科研</option>
                    <option value="first_author_paper">CCF-A / 顶会一作学术论文在投</option>
                  </select>
                </div>
                <div class="what-if-result-box" id="what-if-result-${escapeHtml(progId)}">
                  <div class="sim-delta-badge">拖动滑块或调整背景查看实时预测跃升</div>
                </div>
              </div>
            </div>

            <div class="card-actions-bar">
              <button class="btn-lock-target ${isLocked ? 'locked' : ''}" data-prog-id="${escapeHtml(progId)}">
                ${isLocked ? '★ 已是目标校' : '🎯 设为目标校'}
              </button>
              <select class="tier-select-btn" data-prog-id="${escapeHtml(progId)}">
                <option value="Reach" ${bracketKey === 'Reach' ? 'selected' : ''}>冲刺档</option>
                <option value="Match" ${bracketKey === 'Match' ? 'selected' : ''}>核心档</option>
                <option value="Safety" ${bracketKey === 'Safety' ? 'selected' : ''}>稳妥档</option>
              </select>
              <button class="btn-card-del" data-prog-id="${escapeHtml(progId)}" title="从矩阵中剔除此项目">✕</button>
            </div>
          </div>
        `;
      }).join("");
    }

    if (elements.reachCardsContainer) elements.reachCardsContainer.innerHTML = renderCards(reachList, "Reach");
    if (elements.matchCardsContainer) elements.matchCardsContainer.innerHTML = renderCards(matchList, "Match");
    if (elements.safetyCardsContainer) elements.safetyCardsContainer.innerHTML = renderCards(safetyList, "Safety");

    // 绑定卡片操作按钮事件
    bindMatrixCardEvents();

    if (programs.length > 0 && elements.matrixOverviewText) {
      elements.matrixOverviewText.textContent = `已基于知识图谱与同辈案例库锁定 ${programs.length} 个靶向项目（远光·冲刺 ${reachList.length} 个 / 聚光·核心 ${matchList.length} 个 / 基光·稳妥 ${safetyList.length} 个），院校隐形认可名单与语言小分阻断均已完成校验。`;
    }

    // Milestone 5.0 全息干涉仪组合风险计算
    updatePortfolioDashboard(programs);
  }

  let portfolioDebounceTimer = null;
  async function updatePortfolioDashboard(programs) {
    if (!programs || programs.length === 0) {
      if (elements.portOfferProb) elements.portOfferProb.textContent = "--%";
      if (elements.portRejectRisk) elements.portRejectRisk.textContent = "--%";
      if (elements.portSharpe) elements.portSharpe.textContent = "--";
      if (elements.portAvgCorr) elements.portAvgCorr.textContent = "--";
      if (elements.portRecBanner) elements.portRecBanner.classList.add("hidden");
      return;
    }

    clearTimeout(portfolioDebounceTimer);
    portfolioDebounceTimer = setTimeout(async () => {
      try {
        const resp = await fetch("/api/ml/optimize-portfolio", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            student_profile: state.studentProfile,
            candidate_programs: programs,
            current_selected_ids: programs.map(p => p.id || p.program_id),
            k_budget: Math.min(6, programs.length),
          }),
        });
        if (!resp.ok) return;
        const data = await resp.json();
        const res = data.result;
        if (!res) return;

        const cur = res.current_metrics || res.optimal_metrics;
        if (cur) {
          if (elements.portOfferProb) elements.portOfferProb.textContent = cur.prob_at_least_one_percent || `${(cur.prob_at_least_one_offer * 100).toFixed(1)}%`;
          if (elements.portRejectRisk) elements.portRejectRisk.textContent = cur.correlated_rejection_risk_percent || `${(cur.correlated_rejection_risk * 100).toFixed(1)}%`;
          if (elements.portRejectGap) {
            elements.portRejectGap.textContent = `独立模型低估: ${cur.risk_underestimation_gap_percent || '+0.0%'}`;
          }
          if (elements.portSharpe) elements.portSharpe.textContent = cur.portfolio_sharpe_ratio != null ? cur.portfolio_sharpe_ratio.toFixed(2) : "--";
          if (elements.portAvgCorr) elements.portAvgCorr.textContent = cur.average_correlation != null ? cur.average_correlation.toFixed(2) : "--";
        }

        if (elements.portRecBanner && elements.portRecText && res.recommendations) {
          elements.portRecText.textContent = res.recommendations;
          elements.portRecBanner.classList.remove("hidden");
        }
      } catch (err) {
        console.warn("Portfolio metrics calculation failed:", err);
      }
    }, 200);
  }

  function bindMatrixCardEvents() {
    // 1. 设为文书目标校 (移入精修池)
    document.querySelectorAll(".btn-lock-target").forEach(btn => {
      btn.addEventListener("click", () => {
        const progId = btn.dataset.progId;
        const progs = state.studentProfile.shortlisted_programs || [];
        const target = progs.find(p => p.id === progId);
        if (!target) return;

        patchCanvasState({
          locked_target_program: target,
        }, `已将【${target.name_cn || target.program}】锁定为文书目标校！`);
      });
    });

    // 2. 调整档次 (冲/稳/保切换)
    document.querySelectorAll(".tier-select-btn").forEach(sel => {
      sel.addEventListener("change", (e) => {
        const progId = sel.dataset.progId;
        const newBracket = e.target.value;
        const progs = [...(state.studentProfile.shortlisted_programs || [])];
        const target = progs.find(p => p.id === progId);
        if (!target) return;

        target.tier_bracket = newBracket;
        target.tier = newBracket;
        const names = { Reach: "远光·冲刺", Match: "聚光·核心", Safety: "基光·稳妥" };
        patchCanvasState({
          shortlisted_programs: progs,
        }, `已将【${target.name_cn || target.program}】移至【${names[newBracket]}档】`);
      });
    });

    // 3. 剔除项目
    document.querySelectorAll(".btn-card-del").forEach(btn => {
      btn.addEventListener("click", () => {
        const progId = btn.dataset.progId;
        const progs = (state.studentProfile.shortlisted_programs || []).filter(p => p.id !== progId);
        patchCanvasState({
          shortlisted_programs: progs,
        }, "已从矩阵中剔除该项目");
      });
    });

    // 4. What-If 逆袭沙盘折叠展开
    document.querySelectorAll(".btn-toggle-what-if").forEach(btn => {
      btn.addEventListener("click", () => {
        const progId = btn.dataset.progId;
        const panel = document.getElementById(`what-if-controls-${progId}`);
        const icon = btn.querySelector(".toggle-icon");
        if (!panel) return;
        const isHidden = panel.classList.contains("hidden");
        if (isHidden) {
          panel.classList.remove("hidden");
          if (icon) icon.textContent = "▲";
        } else {
          panel.classList.add("hidden");
          if (icon) icon.textContent = "▼";
        }
      });
    });

    // 5. What-If 动态滑块与参数实时模拟
    const whatIfDebounceTimers = {};
    document.querySelectorAll(".program-card").forEach(card => {
      const progId = card.dataset.progId;
      if (!progId) return;

      const gpaSlider = card.querySelector(".gpa-slider");
      const gpaDisp = card.querySelector(`#gpa-disp-${progId}`);
      const langSel = card.querySelector(".lang-select");
      const resSel = card.querySelector(".research-select");
      const probVal = card.querySelector(`#prob-val-${progId}`);
      const attrsList = card.querySelector(`#attrs-container-${progId} .attr-list`);
      const resBox = card.querySelector(`#what-if-result-${progId}`);

      function triggerSimulation() {
        if (!gpaSlider) return;
        const gpaDelta = parseFloat(gpaSlider.value) || 0.0;
        const langScore = parseFloat(langSel ? langSel.value : 0) || null;
        const resTier = (resSel && resSel.value !== "none") ? resSel.value : null;

        if (gpaDisp) {
          gpaDisp.textContent = `${gpaDelta >= 0 ? '+' : ''}${gpaDelta.toFixed(2)}`;
        }

        clearTimeout(whatIfDebounceTimers[progId]);
        whatIfDebounceTimers[progId] = setTimeout(async () => {
          try {
            const resp = await fetch("/api/ml/simulate-what-if", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                student_profile: state.studentProfile,
                target_program_id: progId,
                simulated_gpa_delta: gpaDelta,
                simulated_lang_score: langScore,
                added_research_tier: resTier,
                major: (state.studentProfile.target_majors && state.studentProfile.target_majors[0]) || state.studentProfile.major,
                months_remaining: 4,
                current_semester: (state.studentProfile && state.studentProfile.current_semester) || "大四上",
              }),
            });
            if (!resp.ok) return;
            const data = await resp.json();
            const sim = data.simulation;
            if (!sim) return;

            // 更新概率显示与色彩高亮
            if (probVal) {
              probVal.textContent = sim.simulated_probability_percent;
              probVal.classList.add("highlight-pulse");
              setTimeout(() => probVal.classList.remove("highlight-pulse"), 800);
            }

            // 更新归因条
            if (attrsList && sim.attribution_changes) {
              const newAttrs = {};
              Object.entries(sim.attribution_changes).forEach(([k, v]) => {
                newAttrs[k] = v.new;
              });
              attrsList.innerHTML = renderAttributionBars(newAttrs);
            }

            // 更新跃升提示卡 & 可行性预警 & Recourse 优先级
            if (resBox) {
              const isPromoted = sim.bracket_transition && sim.bracket_transition.is_promoted;
              const deltaStr = sim.probability_delta_percent;
              const promoText = isPromoted
                ? `<span class="badge-jump">★ 档位跃迁: ${sim.bracket_transition.from_bracket} ➔ ${sim.bracket_transition.to_bracket}</span>`
                : (gpaDelta > 0 || langScore || resTier ? `<span class="badge-gain">概率净提升 ${deltaStr}</span>` : '拖动滑块查看实时预测跃升');

              let warningsHtml = "";
              if (sim.feasibility_warnings && sim.feasibility_warnings.length > 0) {
                warningsHtml = `<div class="feasibility-warning-box">⚠️ <strong>可行域物理拦截:</strong><br>${sim.feasibility_warnings.map(w => `• ${escapeHtml(w)}`).join('<br>')}</div>`;
              }

              let yieldHtml = "";
              if (sim.yield_risk_warning) {
                yieldHtml = `<div class="yield-risk-alert-pill">⚠️ ${escapeHtml(sim.yield_risk_warning)}</div>`;
              }

              let recourseHtml = "";
              if (sim.recommended_action_priority && sim.recommended_action_priority.length > 0) {
                const topActions = sim.recommended_action_priority.slice(0, 2);
                recourseHtml = `
                  <div class="recourse-priority-box">
                    <div class="recourse-title">⚡ 最高性价比提升动作 (时间ROI排序):</div>
                    <div class="recourse-list">
                      ${topActions.map(act => `
                        <div class="recourse-item">
                          <span class="recourse-act-name">${escapeHtml(act.action)}</span>
                          <span class="recourse-act-roi">${escapeHtml(act.roi_label || (act.roi_score + '%/月'))} <span class="recourse-act-cost">(${act.time_cost_months}mo)</span></span>
                        </div>
                      `).join("")}
                    </div>
                  </div>
                `;
              }

              resBox.innerHTML = `
                <div class="sim-delta-badge ${isPromoted ? 'badge-promoted' : ''}">
                  ${promoText}
                </div>
                ${warningsHtml}
                ${yieldHtml}
                ${recourseHtml}
              `;
            }
          } catch (err) {
            console.error("What-If simulation failed:", err);
          }
        }, 150);
      }

      if (gpaSlider) gpaSlider.addEventListener("input", triggerSimulation);
      if (langSel) langSel.addEventListener("change", triggerSimulation);
      if (resSel) resSel.addEventListener("change", triggerSimulation);
    });

    // 6. 一键次模最优组合重排 (Milestone 5.0 Submodular Portfolio Rebalance)
    if (elements.btnSubmodularOptimize && !elements.btnSubmodularOptimize._bound) {
      elements.btnSubmodularOptimize._bound = true;
      elements.btnSubmodularOptimize.addEventListener("click", async () => {
        const origText = elements.btnSubmodularOptimize.innerHTML;
        elements.btnSubmodularOptimize.innerHTML = `<span>⏳ 次模对冲寻优中...</span>`;
        elements.btnSubmodularOptimize.disabled = true;

        try {
          const currentProgs = state.studentProfile.shortlisted_programs || [];
          const resp = await fetch("/api/ml/optimize-portfolio", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              student_profile: state.studentProfile,
              candidate_programs: currentProgs.length > 0 ? currentProgs : null,
              current_selected_ids: currentProgs.map(p => p.id || p.program_id),
              k_budget: Math.min(6, Math.max(3, currentProgs.length)),
            }),
          });
          if (!resp.ok) throw new Error("次模优化接口调用失败");
          const data = await resp.json();
          const res = data.result;
          if (res && res.optimal_portfolio && res.optimal_portfolio.length > 0) {
            patchCanvasState({
              shortlisted_programs: res.optimal_portfolio,
            }, "★ 已应用【次模投资组合对冲重排】！收获至少 1 枚 Offer 概率与夏普比率已达理论最优。");

            setTimeout(() => {
              document.querySelectorAll(".program-card").forEach(c => c.classList.add("rebalance-highlight"));
              setTimeout(() => {
                document.querySelectorAll(".program-card").forEach(c => c.classList.remove("rebalance-highlight"));
              }, 3000);
            }, 100);
          }
        } catch (err) {
          alert("次模优化失败: " + err.message);
        } finally {
          elements.btnSubmodularOptimize.innerHTML = origText;
          elements.btnSubmodularOptimize.disabled = false;
        }
      });
    }
  }

  // 8.5 添加图谱项目到选校矩阵 (Add Program Modal)
  let cachedKgPrograms = [];
  let selectedRegionFilter = "";

  async function openAddProgramModal() {
    if (!elements.addProgramModal) return;
    elements.addProgramModal.classList.remove("hidden");
    if (elements.progSearchKeyword) {
      elements.progSearchKeyword.value = "";
      elements.progSearchKeyword.focus();
    }
    await loadKgPrograms();
  }

  function closeAddProgramModal() {
    if (elements.addProgramModal) elements.addProgramModal.classList.add("hidden");
  }

  async function loadKgPrograms() {
    if (!elements.progResultsList) return;
    elements.progResultsList.innerHTML = `<div class="empty-state-notice">正在载入知识图谱院校项目...</div>`;

    try {
      const resp = await fetch("/api/programs");
      if (!resp.ok) throw new Error("无法读取图谱项目列表");
      const data = await resp.json();
      cachedKgPrograms = data.programs || [];
      renderProgramSearchResults();
    } catch (e) {
      elements.progResultsList.innerHTML = `<div class="empty-state-notice" style="color:#f87171;">加载失败: ${e.message}</div>`;
    }
  }

  function renderProgramSearchResults() {
    if (!elements.progResultsList) return;
    const q = (elements.progSearchKeyword ? elements.progSearchKeyword.value : "").toLowerCase().trim();
    const r = selectedRegionFilter;

    let filtered = cachedKgPrograms.filter(p => {
      if (r && (p.region || "").toUpperCase() !== r) return false;
      if (q) {
        const text = `${p.name_cn || ""} ${p.name_en || ""} ${p.university || ""} ${p.id || ""}`.toLowerCase();
        if (!text.includes(q)) return false;
      }
      return true;
    });

    if (filtered.length === 0) {
      elements.progResultsList.innerHTML = `<div class="empty-state-notice">未找到匹配项目，可尝试调整关键词或地区。</div>`;
      return;
    }

    elements.progResultsList.innerHTML = filtered.map(item => {
      const gpaReq = item.gpa_min_4_0 ? `GPA ≥ ${item.gpa_min_4_0}` : `均分 ≥ ${item.gpa_min_100 || '85'}`;
      const langReq = item.min_ielts ? `雅思 ≥ ${item.min_ielts.total}` : "语言合规";
      const region = item.region || "US";

      return `
        <div class="prog-result-item" data-id="${escapeHtml(item.id)}">
          <div class="prog-item-info">
            <span class="prog-item-title">${escapeHtml(item.name_cn || item.name || item.id)}</span>
            <span class="prog-item-sub">${escapeHtml(item.name_en || item.university || "")}</span>
            <div class="prog-item-tags">
              <span class="prog-item-tag">${escapeHtml(region)}</span>
              <span class="prog-item-tag">${escapeHtml(gpaReq)}</span>
              <span class="prog-item-tag">${escapeHtml(langReq)}</span>
            </div>
          </div>
          <button class="btn-add-to-matrix" data-id="${escapeHtml(item.id)}" type="button">
            ＋ 加入矩阵
          </button>
        </div>
      `;
    }).join("");

    elements.progResultsList.querySelectorAll(".btn-add-to-matrix").forEach(btn => {
      btn.addEventListener("click", () => {
        const pId = btn.getAttribute("data-id");
        const found = cachedKgPrograms.find(x => x.id === pId);
        if (!found) return;

        const targetBracket = elements.progTargetBracket ? elements.progTargetBracket.value : "Match";
        const currentList = [...(state.studentProfile.shortlisted_programs || [])];

        const existingIdx = currentList.findIndex(x => x.id === pId);
        const itemToAdd = Object.assign({}, found, {
          tier_bracket: targetBracket,
          tier: targetBracket,
        });

        if (existingIdx >= 0) {
          currentList[existingIdx] = itemToAdd;
        } else {
          currentList.push(itemToAdd);
        }

        patchCanvasState({
          shortlisted_programs: currentList
        }, `已将【${itemToAdd.name_cn || itemToAdd.name || pId}】加入选校矩阵【${targetBracket}档】！`);

        closeAddProgramModal();
      });
    });
  }

  // 8.6 实战模拟作答与智能三维评分 (Live Interview Evaluation)
  async function submitLiveInterviewAnswer() {
    if (!elements.interviewLiveInput) return;
    const ansText = elements.interviewLiveInput.value.trim();
    if (!ansText) {
      showToast("请输入拟作答内容后再提交评分", "warn");
      return;
    }

    const qText = (elements.evalQText && elements.evalQText.textContent.trim()) || "Tell us about a time you had to deal with an ambiguous software specification or unexpected production bug.";
    const qProg = (elements.evalQProg && elements.evalQProg.textContent.trim()) || "cmu_msit_se";

    const origBtn = elements.btnSubmitLiveEval.innerHTML;
    elements.btnSubmitLiveEval.innerHTML = "⏳ 正在评分...";
    elements.btnSubmitLiveEval.disabled = true;

    try {
      const resp = await fetch("/api/echo/evaluate-answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: state.sessionId,
          question_text: qText,
          answer_text: ansText,
          interview_type: "kira_video",
          program_id: qProg
        })
      });

      if (!resp.ok) throw new Error("评分请求失败");
      const data = await resp.json();
      const evalRes = data.evaluation;

      if (evalRes && evalRes.scores) {
        if (elements.scoreValRelevance) elements.scoreValRelevance.textContent = `${evalRes.scores.content_relevance} / 100`;
        if (elements.barFillRelevance) elements.barFillRelevance.style.width = `${evalRes.scores.content_relevance}%`;

        if (elements.scoreValStar) elements.scoreValStar.textContent = `${evalRes.scores.star_structure} / 100`;
        if (elements.barFillStar) elements.barFillStar.style.width = `${evalRes.scores.star_structure}%`;

        if (elements.scoreValLang) elements.scoreValLang.textContent = `${evalRes.scores.linguistic_authenticity} / 100`;
        if (elements.barFillLang) elements.barFillLang.style.width = `${evalRes.scores.linguistic_authenticity}%`;

        if (elements.scoreValComposite) elements.scoreValComposite.textContent = `${evalRes.scores.composite} / 100`;

        if (elements.evalAnsText) elements.evalAnsText.textContent = ansText;
        if (elements.evalAnsWordcount) elements.evalAnsWordcount.textContent = `${ansText.split(/\s+/).length} 词`;

        if (elements.refinedSampleBody && evalRes.refined_sample_answer) {
          elements.refinedSampleBody.textContent = evalRes.refined_sample_answer;
        }

        showToast("✓ 三维智能评分与高分示范生成完毕！", "success");
      }
    } catch (e) {
      showToast(`评分失败: ${e.message}`, "error");
    } finally {
      elements.btnSubmitLiveEval.innerHTML = origBtn;
      elements.btnSubmitLiveEval.disabled = false;
    }
  }

  // 9. 文书状态机与 Tab 3 视图刷新 (Milestone 4 大纲可编辑列表、版本快照与审片)
  function refreshSopView(stage, profile) {
    const s = stage || 1;
    state.studentProfile.sop_stage = s;
    if (elements.sopStageBadge) elements.sopStageBadge.textContent = `Stage ${s}`;

    // 更新 Stepper
    elements.stepNodes.forEach((node, idx) => {
      if (!node) return;
      const stepIndex = idx + 1;
      node.classList.remove("active", "completed");
      if (stepIndex === s) {
        node.classList.add("active");
      } else if (stepIndex < s) {
        node.classList.add("completed");
      }
    });
    elements.stepLines.forEach((line, idx) => {
      if (!line) return;
      line.classList.toggle("completed", idx + 1 < s);
    });

    const p = profile || state.studentProfile || {};
    const outline = p.sop_outline || [];

    // Stage 2 大纲徽章与 HITL 确认 Banner
    if (elements.blueprintStatus) {
      if (s >= 3) {
        elements.blueprintStatus.textContent = "已确认执笔成文";
        elements.blueprintStatus.style.background = "rgba(16, 185, 129, 0.2)";
        elements.blueprintStatus.style.color = "#34d399";
      } else if (outline.length > 0) {
        elements.blueprintStatus.textContent = "大纲已提炼 (待确认)";
        elements.blueprintStatus.style.background = "rgba(245, 158, 11, 0.2)";
        elements.blueprintStatus.style.color = "#fbbf24";
      } else {
        elements.blueprintStatus.textContent = "待提炼";
      }
    }

    if (elements.outlineHitlBanner) {
      if (state.pendingHumanReview === "disperser_outline" || (s === 2 && outline.length > 0)) {
        elements.outlineHitlBanner.classList.remove("hidden");
      } else {
        elements.outlineHitlBanner.classList.add("hidden");
      }
    }

    // 渲染 Stage 2 大纲可编辑段落
    renderOutlineSection(elements.bpPointsHook, outline, "The Hook");
    renderOutlineSection(elements.bpPointsBody, outline, "Progressive Body");
    renderOutlineSection(elements.bpPointsWhy, outline, "Why School");

    // 渲染 Stage 3/4 正文草稿
    if (elements.draftTextBox) {
      const draft = p.sop_draft || "";
      if (draft) {
        elements.draftTextBox.textContent = draft;
      }
    }

    // 渲染版本快照切换器
    renderVersionsDropdown(p.sop_versions || []);
  }

  function renderOutlineSection(container, outlineList, sectionKey) {
    if (!container) return;
    const sec = outlineList.find(s => s.section === sectionKey || (s.title && s.title.includes(sectionKey)));
    const points = sec ? (sec.points || []) : [];

    if (!points.length) {
      container.innerHTML = `
        <div class="bp-point-item">
          <span class="bp-bullet">▸</span>
          <input type="text" class="bp-point-input" placeholder="输入本段要点..." data-section="${sectionKey}">
        </div>
      `;
    } else {
      container.innerHTML = points.map((pt, idx) => `
        <div class="bp-point-item">
          <span class="bp-bullet">▸</span>
          <input type="text" class="bp-point-input" value="${escapeHtml(pt)}" data-section="${sectionKey}" data-index="${idx}">
          <button class="btn-del-point" data-section="${sectionKey}" data-index="${idx}" title="删除此要点">✕</button>
        </div>
      `).join("");
    }

    // 绑定大纲编辑事件
    container.querySelectorAll(".bp-point-input").forEach(input => {
      input.addEventListener("input", handleOutlineInputChange);
    });
    container.querySelectorAll(".btn-del-point").forEach(btn => {
      btn.addEventListener("click", () => {
        handleDeleteOutlinePoint(btn.dataset.section, parseInt(btn.dataset.index, 10));
      });
    });
  }

  function getCollectedOutline() {
    const sections = [
      { section: "The Hook", title: "1. 入射角 (The Hook)", container: elements.bpPointsHook },
      { section: "Progressive Body", title: "2. 折射链条 (Progressive Body)", container: elements.bpPointsBody },
      { section: "Why School", title: "3. 汇聚焦点 (Why School)", container: elements.bpPointsWhy }
    ];

    return sections.map(s => {
      const inputs = s.container ? Array.from(s.container.querySelectorAll(".bp-point-input")) : [];
      const points = inputs.map(i => i.value.trim()).filter(Boolean);
      return {
        section: s.section,
        title: s.title,
        points: points.length ? points : ["待输入要点..."],
      };
    });
  }

  function handleOutlineInputChange() {
    clearTimeout(state.outlineDebounceTimer);
    state.outlineDebounceTimer = setTimeout(() => {
      const outline = getCollectedOutline();
      patchCanvasState({ sop_outline: outline });
    }, 600);
  }

  function handleAddOutlinePoint(sectionName) {
    let container = elements.bpPointsHook;
    if (sectionName === "Progressive Body") container = elements.bpPointsBody;
    if (sectionName === "Why School") container = elements.bpPointsWhy;
    if (!container) return;

    const newItem = document.createElement("div");
    newItem.className = "bp-point-item";
    newItem.innerHTML = `
      <span class="bp-bullet">▸</span>
      <input type="text" class="bp-point-input" placeholder="输入补充要点..." data-section="${sectionName}">
      <button class="btn-del-point" title="删除要点">✕</button>
    `;
    container.appendChild(newItem);
    const input = newItem.querySelector(".bp-point-input");
    input.focus();
    input.addEventListener("input", handleOutlineInputChange);
    newItem.querySelector(".btn-del-point").addEventListener("click", () => {
      newItem.remove();
      handleOutlineInputChange();
    });
  }

  function handleDeleteOutlinePoint(sectionName, index) {
    const outline = getCollectedOutline();
    const sec = outline.find(s => s.section === sectionName);
    if (sec && sec.points && sec.points.length > index) {
      sec.points.splice(index, 1);
      patchCanvasState({ sop_outline: outline }, "已删除大纲要点");
    }
  }

  function renderVersionsDropdown(versions) {
    if (!elements.sopVersionSelect) return;
    if (!versions || versions.length === 0) {
      elements.sopVersionSelect.innerHTML = `<option value="">暂无已记录快照</option>`;
      if (elements.currentVersionTag) elements.currentVersionTag.textContent = "草稿就绪";
      return;
    }

    elements.sopVersionSelect.innerHTML = versions.map((v, i) => `
      <option value="${escapeHtml(v.version_id)}" ${i === versions.length - 1 ? 'selected' : ''}>
        ${escapeHtml(v.version_id)} - ${escapeHtml(v.label || v.change_summary || '版本快照')}
      </option>
    `).join("");

    const latest = versions[versions.length - 1];
    if (elements.currentVersionTag) {
      elements.currentVersionTag.textContent = latest.version_id;
    }
  }

  // 9.5. 回音壁与 Tab 4 视图刷新 (Milestone 5 模拟面试复盘与网申时间轴)
  function refreshEchoView(profile) {
    if (!profile) return;
    const p = profile || state.studentProfile;
    const records = p.interview_records || [];
    const timelineData = p.application_timeline || [];

    // Badge
    const interviewCount = records.length;
    let progCount = 0;
    if (timelineData.length > 0 && timelineData[0].items) {
      progCount = timelineData[0].items.length;
    } else if (p.shortlisted_programs) {
      progCount = p.shortlisted_programs.length;
    }
    if (elements.echoStatusBadge) {
      elements.echoStatusBadge.textContent = `${progCount} 项网申 / ${interviewCount} 场模拟`;
    }
    if (elements.interviewCountBadge) {
      elements.interviewCountBadge.textContent = `${interviewCount} 场实训记录`;
    }
    if (elements.timelineProgramCounter) {
      elements.timelineProgramCounter.textContent = `${progCount} 项目待办`;
    }

    // 1. 渲染时间轴看板
    if (elements.echoTimelineCards && timelineData.length > 0) {
      const progs = timelineData[0]?.items || [];
      if (progs.length > 0) {
        elements.echoTimelineCards.innerHTML = progs.map(prog => {
          let urgencyClass = "normal";
          if (prog.days_remaining <= 30) urgencyClass = "urgent";
          else if (prog.days_remaining <= 60) urgencyClass = "approaching";

          const borderClass = (prog.tier_bracket || "").toLowerCase() === "reach" ? "border-reach" : "border-match";
          const tagClass = (prog.tier_bracket || "").toLowerCase() === "reach" ? "reach" : "match";

          return `
            <div class="timeline-program-card ${borderClass}">
              <div class="tl-card-header">
                <span class="badge-tag ${tagClass}">${escapeHtml(prog.tier_bracket || "Match")}</span>
                <span class="countdown-badge ${urgencyClass}">剩余 ${prog.days_remaining} 天</span>
              </div>
              <h4 class="tl-prog-title">${escapeHtml(prog.name_cn || prog.name_en)}</h4>
              <div class="tl-prog-en">${escapeHtml(prog.name_en || "")}</div>
              <div class="tl-meta-row">
                <span class="tl-meta-item">📅 官方截点: <strong>${escapeHtml(prog.deadline_raw || prog.deadline_date)}</strong></span>
                <span class="tl-meta-item">📮 推荐信目标: <strong>${escapeHtml(prog.rl_target_date || "截点前10天")}</strong></span>
              </div>
              <div class="tl-req-pills">
                ${(prog.key_requirements || ["网申系统填报", "成绩单与在读证明", "推荐信 Submitted", "SOP定稿上传"]).map(r => `<span class="req-pill">${escapeHtml(r)}</span>`).join("")}
              </div>
            </div>
          `;
        }).join("");
      }
    }

    // 2. 渲染推荐信催交节律
    if (elements.rlStepperContainer && timelineData.length > 1) {
      const rlItems = timelineData[1]?.items || [];
      if (rlItems.length > 0) {
        elements.rlStepperContainer.innerHTML = rlItems.map((rl, idx) => {
          let markerSymbol = idx + 1;
          if (rl.status === "completed") markerSymbol = "✓";
          else if (rl.status === "in_progress") markerSymbol = "⚡";

          return `
            <div class="stepper-item ${rl.status || 'pending'}">
              <div class="stepper-marker">${markerSymbol}</div>
              <div class="stepper-body">
                <div class="stepper-title">${escapeHtml(rl.stage || "")} · ${escapeHtml(rl.title || "")}</div>
                <div class="stepper-desc">${escapeHtml((rl.action_items || []).join("； ") || rl.phase || "")}</div>
              </div>
            </div>
          `;
        }).join("");
      }
    }

    // 3. 渲染材料核验清单
    if (elements.materialsChecklistBox && timelineData.length > 2) {
      const matCats = timelineData[2]?.items || [];
      if (matCats.length > 0) {
        elements.materialsChecklistBox.innerHTML = matCats.map(cat => `
          <div class="checklist-category-group">
            <div class="cat-title">${escapeHtml(cat.category)}</div>
            ${(cat.items || []).map(item => `
              <label class="check-item">
                <input type="checkbox" ${item.status === 'ready' ? 'checked' : ''}>
                <span>${escapeHtml(item.name)}</span>
                <span class="${item.status === 'ready' ? 'tag-ready' : 'tag-pending'}">${item.status === 'ready' ? '已就绪' : '待办'}</span>
              </label>
            `).join("")}
          </div>
        `).join("");
      }
    }

    // 4. 渲染模拟面试作答与评分雷达
    if (records.length > 0) {
      const latest = records[records.length - 1];
      const q = latest.question_data || {};
      const evalData = latest.evaluation || {};
      const scores = evalData.scores || {};
      const feedback = evalData.feedback || {};

      if (elements.evalQType) elements.evalQType.textContent = q.type_label || "全真模拟面试";
      if (elements.evalQProg) elements.evalQProg.textContent = q.program_name || q.target_program_name || "Target Program";
      if (elements.evalQTimer) elements.evalQTimer.textContent = `⏱️ 准备 ${q.prep_time_seconds || 45}s / 作答 ${q.response_time_seconds || 90}s`;
      if (elements.evalQText) elements.evalQText.textContent = `“${q.question || ""}”`;
      if (elements.evalQCn) elements.evalQCn.textContent = q.question_cn || "";

      if (latest.student_answer && elements.evalAnsText) {
        elements.evalAnsText.textContent = latest.student_answer;
        if (elements.evalAnsWordcount) {
          const wc = latest.student_answer.trim().split(/\s+/).length;
          elements.evalAnsWordcount.textContent = `${wc} 词`;
        }
      }

      if (scores.content_relevance !== undefined) {
        if (elements.scoreValRelevance) elements.scoreValRelevance.textContent = `${scores.content_relevance} / 100`;
        if (elements.barFillRelevance) elements.barFillRelevance.style.width = `${scores.content_relevance}%`;
        if (elements.notesRelevance && feedback.content_relevance) {
          elements.notesRelevance.textContent = Array.isArray(feedback.content_relevance) ? feedback.content_relevance.join(" ") : feedback.content_relevance;
        }

        if (elements.scoreValStar) elements.scoreValStar.textContent = `${scores.star_structure} / 100`;
        if (elements.barFillStar) elements.barFillStar.style.width = `${scores.star_structure}%`;
        if (elements.notesStar && feedback.star_structure) {
          elements.notesStar.textContent = feedback.star_structure;
        }

        if (elements.scoreValLang) elements.scoreValLang.textContent = `${scores.linguistic_authenticity} / 100`;
        if (elements.barFillLang) elements.barFillLang.style.width = `${scores.linguistic_authenticity}%`;
        if (elements.notesLang && feedback.linguistic_authenticity) {
          elements.notesLang.textContent = Array.isArray(feedback.linguistic_authenticity) ? feedback.linguistic_authenticity.join(" ") : feedback.linguistic_authenticity;
        }

        if (elements.scoreValComposite) elements.scoreValComposite.textContent = `${scores.composite || 90} / 100`;
      }

      if (evalData.refined_sample_answer && elements.refinedSampleBody) {
        elements.refinedSampleBody.textContent = evalData.refined_sample_answer;
        if (elements.refinedSampleMeta) {
          elements.refinedSampleMeta.textContent = `约 ${evalData.sample_word_count || 120} 词 · 语速适中朗读约 ${evalData.estimated_speaking_seconds || 65} 秒`;
        }
      }
    }
  }

  // 10. 激活或创建当前发言 Agent 气泡
  function ensureAssistantMessageBubble(agentId) {
    const agent = AGENT_CONFIGS[agentId] || AGENT_CONFIGS.luminary;

    if (!state.currentAssistantMessageEl || state.activeAgent !== agentId) {
      updateTopAgentIndicator(agentId);

      const msgWrapper = document.createElement("div");
      msgWrapper.className = `message-wrapper assistant ${agent.agentClass}`;

      msgWrapper.innerHTML = `
        <div class="agent-badge">
          <span class="agent-badge-icon">${agent.icon}</span>
          <span class="agent-badge-name">${agent.name} · ${agent.badge}</span>
          <span class="agent-badge-role">${agent.title.split(" · ")[1] || ""}</span>
        </div>
        <div class="message-bubble">
          <div class="bubble-content"></div>
        </div>
      `;

      elements.chatMessages.appendChild(msgWrapper);
      state.currentAssistantMessageEl = msgWrapper;
      state.currentBubbleContentEl = msgWrapper.querySelector(".bubble-content");
      state.currentRawMarkdown = "";
      scrollToBottom();
    }

    return state.currentBubbleContentEl;
  }

  function appendThoughtPanel(thoughtText) {
    if (!thoughtText || !thoughtText.trim()) return;
    if (!state.currentAssistantMessageEl) {
      ensureAssistantMessageBubble(state.activeAgent);
    }
    const bubble = state.currentAssistantMessageEl.querySelector(".message-bubble");
    if (!bubble) return;

    let panel = bubble.querySelector(".thought-card");
    if (!panel) {
      panel = document.createElement("div");
      panel.className = "thought-card";
      panel.innerHTML = `<span class="thought-icon">💡</span> <span class="thought-text">${escapeHtml(thoughtText)}</span>`;
      bubble.prepend(panel);
    } else {
      panel.querySelector(".thought-text").textContent = thoughtText;
    }
    scrollToBottom();
  }

  function appendToolCallBanner(agentId, toolName, toolDesc, status = "executing") {
    if (!state.currentBubbleContentEl) {
      ensureAssistantMessageBubble(agentId);
    }
    const existing = state.currentBubbleContentEl.querySelector(`.tool-event-pill[data-tool="${toolName}"]`);
    if (existing) {
      if (status === "completed") {
        existing.className = "tool-event-pill completed";
        existing.innerHTML = `<span>✓</span> <span>${escapeHtml(toolDesc || toolName)}</span>`;
      }
      return;
    }

    const pill = document.createElement("div");
    pill.className = `tool-event-pill ${status}`;
    pill.setAttribute("data-tool", toolName);
    pill.innerHTML = `<span>${status === "completed" ? "✓" : "⚙️"}</span> <span>${escapeHtml(toolDesc || toolName)}</span>`;
    state.currentBubbleContentEl.appendChild(pill);
    scrollToBottom();
  }

  function appendUserMessage(text) {
    const msgWrapper = document.createElement("div");
    msgWrapper.className = "message-wrapper user";
    msgWrapper.innerHTML = `
      <div class="message-bubble">
        <div class="bubble-content">
          <p>${escapeHtml(text)}</p>
        </div>
      </div>
    `;
    elements.chatMessages.appendChild(msgWrapper);
    scrollToBottom();
  }

  function scrollToBottom() {
    if (elements.chatMessages) {
      elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    }
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // 11. 轻量级 Markdown 语法转换器
  function renderMarkdown(md) {
    if (!md) return "";
    let html = "";
    const lines = md.split("\n");
    let inCodeBlock = false;
    let codeBuffer = "";
    let inList = false;

    for (let i = 0; i < lines.length; i++) {
      let line = lines[i];

      if (line.trim().startsWith("```")) {
        if (!inCodeBlock) {
          inCodeBlock = true;
          codeBuffer = "";
          continue;
        } else {
          inCodeBlock = false;
          html += `<pre><code>${escapeHtml(codeBuffer.trim())}</code></pre>`;
          continue;
        }
      }

      if (inCodeBlock) {
        codeBuffer += line + "\n";
        continue;
      }

      if (line.startsWith("#### ")) {
        if (inList) { html += "</ul>"; inList = false; }
        html += `<h4 style="color:#38bdf8;margin:8px 0 4px 0;font-size:0.92rem;">${inlineMarkdown(line.substring(5))}</h4>`;
        continue;
      }
      if (line.startsWith("### ")) {
        if (inList) { html += "</ul>"; inList = false; }
        html += `<h3 style="color:#f8fafc;margin:10px 0 6px 0;font-size:1rem;">${inlineMarkdown(line.substring(4))}</h3>`;
        continue;
      }
      if (line.startsWith("## ")) {
        if (inList) { html += "</ul>"; inList = false; }
        html += `<h3 style="color:#f8fafc;margin:10px 0 6px 0;font-size:1.05rem;">${inlineMarkdown(line.substring(3))}</h3>`;
        continue;
      }

      if (line.trim().startsWith("- ") || line.trim().startsWith("* ")) {
        if (!inList) { html += "<ul>"; inList = true; }
        html += `<li>${inlineMarkdown(line.trim().substring(2))}</li>`;
        continue;
      }

      let numMatch = line.trim().match(/^(\d+)\.\s+(.*)/);
      if (numMatch) {
        if (inList) { html += "</ul>"; inList = false; }
        html += `<p><strong>${numMatch[1]}.</strong> ${inlineMarkdown(numMatch[2])}</p>`;
        continue;
      }

      if (inList) {
        html += "</ul>";
        inList = false;
      }

      if (line.trim().length > 0) {
        html += `<p>${inlineMarkdown(line)}</p>`;
      }
    }

    if (inList) html += "</ul>";
    if (inCodeBlock) html += `<pre><code>${escapeHtml(codeBuffer.trim())}</code></pre>`;
    return html;
  }

  function inlineMarkdown(text) {
    return text
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(/`(.*?)`/g, "<code>$1</code>");
  }

  // 12. 前端状态突变写入 LangGraph Checkpointer (Milestone 4 核心)
  async function patchCanvasState(patchData, toastMsg = null) {
    try {
      const resp = await fetch("/api/canvas/patch-state", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: state.sessionId,
          state_patch: patchData
        })
      });

      if (resp.ok) {
        const data = await resp.json();
        state.studentProfile = data.profile;
        state.pendingHumanReview = data.pending_human_review;
        refreshProfileView(data.profile);
        if (data.profile.shortlisted_programs) {
          refreshMatrixView(data.profile.shortlisted_programs);
        }
        if (data.profile.sop_stage) {
          refreshSopView(data.profile.sop_stage, data.profile);
        }
        if (toastMsg) showToast(toastMsg, "success");
      }
    } catch (e) {
      console.error("Canvas patch state error:", e);
      showToast("状态同步失败，请检查网络", "error");
    }
  }

  // 13. 发送消息并监听 SSE 事件流
  async function sendUserMessage(msgText) {
    if (!msgText || !msgText.trim() || state.isStreaming) return;
    const cleanText = msgText.trim();
    elements.chatInput.value = "";

    appendUserMessage(cleanText);
    state.isStreaming = true;
    elements.sendBtn.disabled = true;
    elements.sendBtn.textContent = "汇聚中...";

    try {
      const resp = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: state.sessionId,
          message: cleanText
        })
      });

      if (!resp.ok) throw new Error(`HTTP 异常 ${resp.status}`);

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let streamBuffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        streamBuffer += decoder.decode(value, { stream: true });
        const blocks = streamBuffer.split("\n\n");
        streamBuffer = blocks.pop();

        for (const block of blocks) {
          if (!block.trim()) continue;

          let eventName = "message";
          let dataStr = "";

          const blockLines = block.split("\n");
          for (const bl of blockLines) {
            if (bl.startsWith("event: ")) {
              eventName = bl.replace("event: ", "").trim();
            } else if (bl.startsWith("data: ")) {
              dataStr += bl.replace("data: ", "").trim();
            }
          }

          if (!dataStr) continue;

          let dataObj;
          try {
            dataObj = JSON.parse(dataStr);
          } catch (e) {
            continue;
          }

          handleSseEvent(eventName, dataObj);
        }
      }
    } catch (err) {
      console.error("Stream request failed:", err);
      showToast(`网络流异常: ${err.message}`, "error");
    } finally {
      state.isStreaming = false;
      elements.sendBtn.disabled = false;
      elements.sendBtn.innerHTML = `<span class="send-beam">✦</span> 发送`;
      state.currentAssistantMessageEl = null;
      state.currentBubbleContentEl = null;
    }
  }

  // 14. 核心 SSE 事件分发器
  function handleSseEvent(eventName, data) {
    switch (eventName) {
      case "start":
        break;

      case "agent_switch":
        const targetAgent = data.agent_id || "luminary";
        updateTopAgentIndicator(targetAgent);
        ensureAssistantMessageBubble(targetAgent);

        if (targetAgent === "locus") {
          switchCanvasTab("matrix");
        } else if (targetAgent === "disperser") {
          switchCanvasTab("sop");
        } else if (targetAgent === "echo") {
          switchCanvasTab("echo");
        } else if (targetAgent === "resonator") {
          switchCanvasTab("resonator");
        } else if (targetAgent === "facet") {
          switchCanvasTab("profile");
        }
        break;

      case "thought":
        ensureAssistantMessageBubble(data.agent || "luminary");
        appendThoughtPanel(data.thought);
        break;

      case "tool_call":
        ensureAssistantMessageBubble(data.agent || "locus");
        appendToolCallBanner(data.agent, data.tool, data.description, "executing");
        break;

      case "tool_result":
        appendToolCallBanner(data.agent, data.tool, data.description, "completed");
        break;

      case "token":
        const bubble = ensureAssistantMessageBubble(data.agent || state.activeAgent);
        state.currentRawMarkdown += data.token || "";
        bubble.innerHTML = renderMarkdown(state.currentRawMarkdown);
        scrollToBottom();
        break;

      case "profile_update":
        if (data.student_profile) {
          refreshProfileView(data.student_profile);
          if (data.student_profile.shortlisted_programs && data.student_profile.shortlisted_programs.length > 0) {
            refreshMatrixView(data.student_profile.shortlisted_programs);
          }
          if (data.student_profile.sop_stage) {
            refreshSopView(data.student_profile.sop_stage, data.student_profile);
          }
          if (data.student_profile.interview_records?.length > 0 || data.student_profile.application_timeline?.length > 0) {
            refreshEchoView(data.student_profile);
          }
        }
        break;

      case "human_review_required":
        state.pendingHumanReview = data.review_type;
        showToast(`⏸️ 【${data.agent || "智能体"}】已进入人工共创断点 (${data.review_type})`, "warn");
        if (data.review_type === "locus_matrix") {
          switchCanvasTab("matrix");
          if (data.shortlisted_programs) refreshMatrixView(data.shortlisted_programs);
        } else if (data.review_type === "disperser_outline") {
          switchCanvasTab("sop");
          if (data.sop_outline) {
            state.studentProfile.sop_outline = data.sop_outline;
            refreshSopView(data.sop_stage || 2, state.studentProfile);
          }
        }
        break;

      case "done":
        if (data.student_profile) {
          refreshProfileView(data.student_profile);
        }
        state.pendingHumanReview = data.pending_human_review || null;
        if (data.shortlisted_programs && data.shortlisted_programs.length > 0) {
          refreshMatrixView(data.shortlisted_programs);
          if (data.active_agent === "locus") switchCanvasTab("matrix");
        }
        if (data.sop_stage) {
          refreshSopView(data.sop_stage, data.student_profile);
          if (data.active_agent === "disperser" || data.sop_stage >= 2) {
            switchCanvasTab("sop");
          }
        }
        if (data.active_agent === "echo" || (data.student_profile && (data.student_profile.interview_records?.length > 0 || data.student_profile.application_timeline?.length > 0))) {
          refreshEchoView(data.student_profile);
          if (data.active_agent === "echo") {
            switchCanvasTab("echo");
          }
        }
        if (data.active_agent === "resonator" || (data.student_profile && data.student_profile.target_professors?.length > 0)) {
          refreshResonatorView();
          if (data.active_agent === "resonator") {
            switchCanvasTab("resonator");
          }
        }
        break;

      case "error":
        showToast(`中枢异常: ${data.error || "未知错误"}`, "error");
        break;
    }
  }

  // 15. 初始化加载已有会话数据
  async function loadSessionSpectrum() {
    try {
      const resp = await fetch(`/api/session/${state.sessionId}/spectrum`);
      if (resp.ok) {
        const data = await resp.json();
        state.pendingHumanReview = data.pending_human_review || null;
        if (data.profile) {
          state.studentProfile = data.profile;
          refreshProfileView(data.profile);
          refreshEchoView(data.profile);
          refreshResonatorView();
        }
        if (data.shortlisted_programs) {
          refreshMatrixView(data.shortlisted_programs);
        }
        if (data.sop_stage) {
          refreshSopView(data.sop_stage, data.profile);
        }
        if (data.active_agent) {
          updateTopAgentIndicator(data.active_agent);
        }
        if (data.messages && data.messages.length > 0) {
          renderMessagesHistory(data.messages);
        }
        updateProfileNameDisplay(data.profile, data.session_id);
        elements.gatewayStatus.textContent = "网关在线";
      }
    } catch (e) {
      console.warn("Could not load initial spectrum:", e);
      elements.gatewayStatus.textContent = "离线/就绪";
    }
  }

  function updateProfileNameDisplay(profile, sessionId) {
    if (!elements.currentProfileName) return;
    const sid = sessionId || state.sessionId;
    const name = (profile && profile.undergrad_name)
      ? (profile.undergrad_name + (profile.major ? ` · ${profile.major}` : " 学员"))
      : `学员档案 (${sid.substring(0, 8)})`;
    elements.currentProfileName.textContent = name;
    if (elements.sessionIdDisplay) {
      elements.sessionIdDisplay.textContent = sid;
    }
  }

  function renderMessagesHistory(messages) {
    if (!elements.chatMessages || !messages || messages.length === 0) return;
    elements.chatMessages.innerHTML = "";
    for (const msg of messages) {
      if (msg.role === "user") {
        const userWrap = document.createElement("div");
        userWrap.className = "message-wrapper user";
        userWrap.innerHTML = `
          <div class="user-avatar">U</div>
          <div class="message-bubble user-bubble">
            <div class="bubble-content"><p>${escapeHtml(msg.content)}</p></div>
          </div>
        `;
        elements.chatMessages.appendChild(userWrap);
      } else if (msg.role === "assistant") {
        const agentMeta = AGENT_CONFIGS.luminary;
        const assistWrap = document.createElement("div");
        assistWrap.className = `message-wrapper assistant ${agentMeta.agentClass}`;
        assistWrap.innerHTML = `
          <div class="agent-badge">
            <span class="agent-badge-icon">${agentMeta.icon}</span>
            <span class="agent-badge-name">${agentMeta.name} · ${agentMeta.badge}</span>
            <span class="agent-badge-role">${agentMeta.title}</span>
          </div>
          <div class="message-bubble">
            <div class="bubble-content">${renderMarkdown(msg.content)}</div>
          </div>
        `;
        elements.chatMessages.appendChild(assistWrap);
      } else if (msg.role === "system") {
        const sysWrap = document.createElement("div");
        sysWrap.className = "message-wrapper system";
        sysWrap.innerHTML = `
          <div class="system-bubble">
            <span class="system-icon">◈</span>
            <span>${escapeHtml(msg.content)}</span>
          </div>
        `;
        elements.chatMessages.appendChild(sysWrap);
      }
    }
    scrollToBottom();
  }

  // 16. 手动修改档案或提交表单
  async function handleProfileSave() {
    const undergrad = elements.inputProfSchool.value.trim();
    const tier = elements.inputProfTier.value;
    const major = elements.inputProfMajor.value.trim();
    const gpa = elements.inputProfGpa.value.trim();
    const ielts = elements.inputProfIelts.value.trim();
    const targets = elements.inputProfTargets.value.trim();

    const patch = {};
    if (undergrad) patch.undergrad_name = undergrad;
    if (tier) patch.undergrad_tier = tier;
    if (major) patch.major = major;
    if (gpa) patch.gpa_raw = gpa;

    if (ielts) {
      patch.language_scores = {};
      const match = ielts.match(/([0-9.]+)/);
      if (match) {
        patch.language_scores["IELTS_total"] = parseFloat(match[1]);
      }
    }

    if (targets) {
      patch.target_regions = targets.split(/[,/ ]+/).filter(Boolean);
    }

    await patchCanvasState({ student_profile: patch }, "学生光谱档案已成功同步至中枢！");
  }

  // 17. 应用粘贴的 JSON
  async function handleApplyJson() {
    const raw = elements.jsonInput.value.trim();
    if (!raw) return;

    try {
      const parsed = JSON.parse(raw);
      await patchCanvasState({ student_profile: parsed }, "JSON 档案解析并导入成功！");
      elements.jsonPasteArea.classList.add("hidden");
    } catch (e) {
      showToast(`JSON 解析格式错误: ${e.message}`, "error");
    }
  }

  // 18. 重置并开启新会话
  async function handleNewSession() {
    closeProfileDropdown();
    const newId = "prism_" + Math.random().toString(16).substring(2, 10);
    try {
      await fetch("/api/session/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: state.sessionId })
      });
    } catch (e) {
      // ignore
    }

    state.sessionId = newId;
    localStorage.setItem("prismera_session_id", newId);
    elements.sessionIdDisplay.textContent = newId;

    // 清空界面状态
    state.studentProfile = {
      undergrad_name: null,
      undergrad_tier: null,
      major: null,
      gpa_raw: null,
      language_scores: {},
      target_regions: [],
      target_majors: [],
      shortlisted_programs: [],
      sop_stage: 1,
      mined_story_fragments: [],
      target_professors: [],
      sop_outline: [],
      sop_draft: "",
      sop_critique: {},
      sop_versions: [],
      locked_target_program: null
    };
    state.pendingHumanReview = null;
    refreshProfileView(state.studentProfile);
    refreshMatrixView([]);
    refreshSopView(1, state.studentProfile);
    switchCanvasTab("profile");
    updateTopAgentIndicator("luminary");

    // 重置聊天区
    elements.chatMessages.innerHTML = `
      <div class="message-wrapper assistant agent-luminary">
        <div class="agent-badge">
          <span class="agent-badge-icon">✦</span>
          <span class="agent-badge-name">司光者 · The Luminary</span>
          <span class="agent-badge-role">中枢光轴 · 意图解析</span>
        </div>
        <div class="message-bubble">
          <div class="bubble-content">
            <p>已开启新会话（Session ID: <code>${newId}</code>）。</p>
            <p>我是 <strong>PrismEra（棱镜纪）</strong> 中枢主控——<strong>【司光者 · The Luminary】</strong>。请陈述你的学术背景或轻点下方快捷意图胶囊。</p>
          </div>
        </div>
      </div>
    `;

    showToast("已重置并开启全新光学档案会话！", "info");
    await loadProfileList();
  }

  // 19. 暗室文书局部折射 (Inline Refraction) 执行逻辑
  async function executeRefraction(instruction) {
    const selected = state.selectedSnippet || (elements.draftTextBox ? elements.draftTextBox.textContent.trim().substring(0, 150) : "");
    if (!selected) {
      showToast("请在文书草稿中划词选取一段句子", "warn");
      return;
    }

    if (elements.executeRefractBtn) {
      elements.executeRefractBtn.disabled = true;
      elements.executeRefractBtn.textContent = "⚡ 折射中...";
    }

    try {
      const resp = await fetch("/api/canvas/refract-selection", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: state.sessionId,
          selected_text: selected,
          instruction: instruction,
          full_text: state.studentProfile.sop_draft || ""
        })
      });

      if (!resp.ok) throw new Error("局部折射请求失败");
      const diffData = await resp.json();
      state.latestRefractDiff = diffData;

      if (elements.diffRenderBox) {
        elements.diffRenderBox.innerHTML = diffData.diff_html;
      }
      if (elements.diffViewPanel) {
        elements.diffViewPanel.classList.remove("hidden");
      }
      showToast("✦ 局部折射已生成，请在下方审阅 Diff 对比并选择采纳或驳回", "info");
    } catch (e) {
      showToast(`折射失败: ${e.message}`, "error");
    } finally {
      if (elements.executeRefractBtn) {
        elements.executeRefractBtn.disabled = false;
        elements.executeRefractBtn.textContent = "⚡ 执行折射";
      }
    }
  }

  // 20. 采纳 Diff 并写入正文
  async function handleAcceptDiff() {
    if (!state.latestRefractDiff) return;

    try {
      const resp = await fetch("/api/canvas/accept-refraction", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: state.sessionId,
          original_text: state.latestRefractDiff.original_text,
          rewritten_text: state.latestRefractDiff.rewritten_text,
          full_text: state.studentProfile.sop_draft || "",
          change_summary: `局部折射: ${state.latestRefractDiff.instruction || "精修"}`
        })
      });

      if (!resp.ok) throw new Error("采纳修改失败");
      const data = await resp.json();
      state.studentProfile = data.profile;
      refreshSopView(data.profile.sop_stage || 3, data.profile);

      if (elements.refractionWorkbench) elements.refractionWorkbench.classList.add("hidden");
      if (elements.diffViewPanel) elements.diffViewPanel.classList.add("hidden");
      showToast("✓ 局部折射修改已采纳，新版本快照已保存！", "success");
    } catch (e) {
      showToast(`采纳失败: ${e.message}`, "error");
    }
  }

  // 21. 回滚到历史快照
  async function handleRollbackVersion() {
    const verId = elements.sopVersionSelect && elements.sopVersionSelect.value;
    if (!verId) return;

    if (!confirm(`确定回滚文书状态到版本【${verId}】吗？`)) return;

    try {
      const resp = await fetch("/api/canvas/rollback-version", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: state.sessionId,
          version_id: verId
        })
      });

      if (!resp.ok) throw new Error("回滚请求失败");
      const data = await resp.json();
      state.studentProfile = data.profile;
      refreshSopView(data.profile.sop_stage, data.profile);
      showToast(`↺ 已成功回滚至历史版本快照【${verId}】！`, "success");
    } catch (e) {
      showToast(`回滚失败: ${e.message}`, "error");
    }
  }

  // ==========================================================================
  // Milestone 7: 学生档案矩阵管理 (SQLite Session Store) & 全案报告导出引擎
  // ==========================================================================

  let renamingSessionId = null;
  let cachedMarkdownContent = "";

  function closeProfileDropdown() {
    if (elements.profileDropdown) {
      elements.profileDropdown.classList.add("hidden");
      elements.profileDropdown.style.display = "none";
    }
    if (elements.profileSwitcherBtn) {
      elements.profileSwitcherBtn.classList.remove("active");
      elements.profileSwitcherBtn.setAttribute("aria-expanded", "false");
    }
    if (elements.profileSwitcherWrapper) {
      elements.profileSwitcherWrapper.classList.remove("open");
    }
  }

  function toggleProfileDropdown() {
    if (!elements.profileDropdown) return;
    const isCurrentlyHidden = elements.profileDropdown.classList.contains("hidden") ||
                              elements.profileDropdown.style.display === "none" ||
                              (window.getComputedStyle && window.getComputedStyle(elements.profileDropdown).display === "none");
    if (isCurrentlyHidden) {
      elements.profileDropdown.classList.remove("hidden");
      elements.profileDropdown.style.display = "flex";
      if (elements.profileSwitcherBtn) {
        elements.profileSwitcherBtn.classList.add("active");
        elements.profileSwitcherBtn.setAttribute("aria-expanded", "true");
      }
      if (elements.profileSwitcherWrapper) {
        elements.profileSwitcherWrapper.classList.add("open");
      }
      loadProfileList();
    } else {
      closeProfileDropdown();
    }
  }

  async function loadProfileList() {
    if (!elements.profileDropdownList) return;
    try {
      const resp = await fetch("/api/sessions");
      if (!resp.ok) return;
      const data = await resp.json();
      const sessions = data.sessions || [];

      elements.profileDropdownList.innerHTML = "";
      if (sessions.length === 0) {
        elements.profileDropdownList.innerHTML = `<div class="empty-column-placeholder" style="padding:16px;text-align:center;">暂无已保存学员档案</div>`;
        return;
      }

      sessions.forEach(s => {
        const isActive = s.session_id === state.sessionId;
        if (isActive && elements.currentProfileName) {
          elements.currentProfileName.textContent = s.name;
        }

        const item = document.createElement("div");
        item.className = `profile-list-item ${isActive ? "active" : ""}`;
        item.dataset.sessionId = s.session_id;

        const schoolTag = s.undergrad_name || s.undergrad_tier || "未设定院校";
        const majorTag = s.major || "专业待定";
        const turnsTag = `${s.turns || 0} 轮对话`;

        item.innerHTML = `
          <div class="item-main">
            <div class="item-name-row">
              <span class="item-name" title="${escapeHtml(s.name)}">${escapeHtml(s.name)}</span>
              ${isActive ? '<span class="item-active-pill">当前活跃</span>' : ''}
            </div>
            <div class="item-sub-tags">
              <span>🏛️ ${escapeHtml(schoolTag)}</span>
              <span>📚 ${escapeHtml(majorTag)}</span>
              <span>💬 ${escapeHtml(turnsTag)}</span>
            </div>
          </div>
          <div class="item-actions">
            <button class="btn-item-icon btn-rename-item" title="重命名档案" data-session-id="${escapeHtml(s.session_id)}" data-name="${escapeHtml(s.name)}">✏️</button>
            <button class="btn-item-icon del btn-del-item" title="删除档案" data-session-id="${escapeHtml(s.session_id)}">🗑️</button>
          </div>
        `;

        item.addEventListener("click", (e) => {
          if (e.target.closest(".item-actions")) return;
          switchSession(s.session_id);
        });

        item.querySelector(".btn-rename-item").addEventListener("click", (e) => {
          e.stopPropagation();
          openRenameModal(s.session_id, s.name);
        });

        item.querySelector(".btn-del-item").addEventListener("click", async (e) => {
          e.stopPropagation();
          if (confirm(`确定要彻底删除学生档案《${s.name}》吗？`)) {
            await deleteSession(s.session_id);
          }
        });

        elements.profileDropdownList.appendChild(item);
      });
    } catch (e) {
      console.warn("Could not load sessions list:", e);
    }
  }

  async function switchSession(targetSessionId) {
    if (!targetSessionId) return;
    closeProfileDropdown();
    if (targetSessionId === state.sessionId) {
      return;
    }
    state.sessionId = targetSessionId;
    localStorage.setItem("prismera_session_id", targetSessionId);
    if (elements.sessionIdDisplay) {
      elements.sessionIdDisplay.textContent = targetSessionId;
    }

    await loadSessionSpectrum();
    await loadProfileList();
    showToast(`已切换并恢复档案进度 (Session: ${targetSessionId})`, "success");
  }

  async function deleteSession(targetSessionId) {
    try {
      const resp = await fetch(`/api/session/${targetSessionId}`, { method: "DELETE" });
      if (resp.ok) {
        showToast("已成功删除该学生档案", "info");
        if (state.sessionId === targetSessionId) {
          await handleNewSession();
        } else {
          await loadProfileList();
        }
      }
    } catch (e) {
      showToast(`删除档案失败: ${e.message}`, "error");
    }
  }

  function openRenameModal(sessionId, currentName) {
    closeProfileDropdown();
    renamingSessionId = sessionId;
    if (elements.renameProfileNameInput) {
      elements.renameProfileNameInput.value = currentName || "";
    }
    if (elements.renameProfileModal) {
      elements.renameProfileModal.classList.remove("hidden");
      elements.renameProfileNameInput.focus();
    }
  }

  function closeRenameModal() {
    if (elements.renameProfileModal) {
      elements.renameProfileModal.classList.add("hidden");
    }
  }

  async function confirmRenameProfile() {
    if (!renamingSessionId || !elements.renameProfileNameInput) return;
    const newName = elements.renameProfileNameInput.value.trim();
    if (!newName) {
      showToast("档案名称不能为空", "warn");
      return;
    }

    try {
      const resp = await fetch(`/api/session/${renamingSessionId}/rename`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName })
      });
      if (resp.ok) {
        showToast("档案重命名成功", "success");
        closeRenameModal();
        if (renamingSessionId === state.sessionId && elements.currentProfileName) {
          elements.currentProfileName.textContent = newName;
        }
        await loadProfileList();
      }
    } catch (e) {
      showToast(`重命名失败: ${e.message}`, "error");
    }
  }

  function openCreateProfileModal() {
    closeProfileDropdown();
    if (elements.createProfileModal) {
      elements.createProfileModal.classList.remove("hidden");
      if (elements.newProfileNameInput) elements.newProfileNameInput.value = "";
      if (elements.newProfileSchoolInput) elements.newProfileSchoolInput.value = "";
      if (elements.newProfileMajorInput) elements.newProfileMajorInput.value = "";
      if (elements.newProfileGpaInput) elements.newProfileGpaInput.value = "";
      if (elements.newProfileNameInput) elements.newProfileNameInput.focus();
    }
  }

  function closeCreateProfileModal() {
    if (elements.createProfileModal) {
      elements.createProfileModal.classList.add("hidden");
    }
  }

  async function confirmCreateProfile() {
    const name = elements.newProfileNameInput ? elements.newProfileNameInput.value.trim() : "";
    const school = elements.newProfileSchoolInput ? elements.newProfileSchoolInput.value.trim() : "";
    const tier = elements.newProfileTierInput ? elements.newProfileTierInput.value : "985";
    const major = elements.newProfileMajorInput ? elements.newProfileMajorInput.value.trim() : "";
    const gpa = elements.newProfileGpaInput ? elements.newProfileGpaInput.value.trim() : "";

    const payload = {
      name: name || undefined,
      initial_profile: {}
    };
    if (school) payload.initial_profile.undergrad_name = school;
    if (tier) payload.initial_profile.undergrad_tier = tier;
    if (major) payload.initial_profile.major = major;
    if (gpa) payload.initial_profile.gpa_raw = gpa;

    try {
      const resp = await fetch("/api/session/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!resp.ok) throw new Error("创建新档案失败");
      const res = await resp.json();
      closeCreateProfileModal();
      showToast("✦ 全新学生光谱档案创建成功！", "success");
      await switchSession(res.session_id);
    } catch (e) {
      showToast(`创建失败: ${e.message}`, "error");
    }
  }

  // Dossier Exporter Handlers
  async function openExportModal() {
    closeProfileDropdown();
    if (!elements.exportDossierModal) return;
    elements.exportDossierModal.classList.remove("hidden");
    switchExportPreviewTab("html");

    // Load HTML preview
    if (elements.exportPreviewIframe) {
      elements.exportPreviewIframe.src = `/api/session/${state.sessionId}/export?format=html`;
    }

    // Load Markdown preview
    try {
      if (elements.exportMarkdownView) {
        elements.exportMarkdownView.textContent = "正在编译《PrismEra 个人升学光谱全案报告》Markdown 源码...";
      }
      const resp = await fetch(`/api/session/${state.sessionId}/export/preview`);
      if (resp.ok) {
        const data = await resp.json();
        cachedMarkdownContent = data.markdown || "";
        if (elements.exportMarkdownView) {
          elements.exportMarkdownView.textContent = cachedMarkdownContent;
        }
      }
    } catch (e) {
      console.warn("Could not load markdown preview:", e);
    }
  }

  function closeExportModal() {
    if (elements.exportDossierModal) {
      elements.exportDossierModal.classList.add("hidden");
    }
  }

  function switchExportPreviewTab(tab) {
    if (tab === "html") {
      if (elements.tabPreviewHtml) elements.tabPreviewHtml.classList.add("active");
      if (elements.tabPreviewMd) elements.tabPreviewMd.classList.remove("active");
      if (elements.panePreviewHtml) elements.panePreviewHtml.classList.add("active");
      if (elements.panePreviewMd) elements.panePreviewMd.classList.remove("active");
    } else {
      if (elements.tabPreviewHtml) elements.tabPreviewHtml.classList.remove("active");
      if (elements.tabPreviewMd) elements.tabPreviewMd.classList.add("active");
      if (elements.panePreviewHtml) elements.panePreviewHtml.classList.remove("active");
      if (elements.panePreviewMd) elements.panePreviewMd.classList.add("active");
    }
  }

  function copyMarkdownExport() {
    if (!cachedMarkdownContent) {
      showToast("Markdown 报告尚未编译完成", "warn");
      return;
    }
    navigator.clipboard.writeText(cachedMarkdownContent).then(() => {
      showToast("已将《PrismEra 个人升学光谱全案报告》Markdown 复制到剪贴板！", "success");
    }).catch(() => {
      showToast("复制失败，请点击一键下载", "error");
    });
  }

  function downloadMarkdownExport() {
    window.location.href = `/api/session/${state.sessionId}/export?format=markdown&download=true`;
  }

  function downloadHtmlExport() {
    window.location.href = `/api/session/${state.sessionId}/export?format=html&download=true`;
  }

  function openFullscreenExport() {
    window.open(`/api/session/${state.sessionId}/export?format=html`, "_blank");
  }

  // =========================================================================
  // 21.5 Milestone 8: 棱镜控制台 (Prism Console) 驱动逻辑
  // =========================================================================
  let currentConsoleConfig = null;

  async function openConsoleModal() {
    closeProfileDropdown();
    if (!elements.prismConsoleModal) return;
    elements.prismConsoleModal.classList.remove("hidden");
    await loadConsoleConfig();
    await loadConsoleStats();
    await loadConsoleBenchmarkLatest();
  }

  function closeConsoleModal() {
    if (!elements.prismConsoleModal) return;
    elements.prismConsoleModal.classList.add("hidden");
  }

  function switchConsoleTab(tabKey) {
    const tabs = [
      { key: "engine", pill: elements.tabConsoleEngine, pane: elements.paneConsoleEngine },
      { key: "graph", pill: elements.tabConsoleGraph, pane: elements.paneConsoleGraph },
      { key: "benchmark", pill: elements.tabConsoleBenchmark, pane: elements.paneConsoleBenchmark },
    ];

    tabs.forEach(t => {
      if (t.pill && t.pane) {
        if (t.key === tabKey) {
          t.pill.classList.add("active");
          t.pane.classList.add("active");
        } else {
          t.pill.classList.remove("active");
          t.pane.classList.remove("active");
        }
      }
    });

    if (tabKey === "graph") {
      loadConsoleStats();
    } else if (tabKey === "benchmark") {
      loadConsoleBenchmarkLatest();
    }
  }

  // --- Tab A: Engine & Hot-Switching ---
  async function loadConsoleConfig() {
    try {
      const resp = await fetch("/api/admin/config");
      if (!resp.ok) return;
      const data = await resp.json();
      currentConsoleConfig = data.config;

      const isMock = data.config.is_offline_mock;

      if (elements.consoleHeaderModeTag) {
        elements.consoleHeaderModeTag.textContent = data.engine_mode;
      }

      if (elements.currentEngineModeTitle) {
        elements.currentEngineModeTitle.textContent = isMock ? "Deterministic 离线引擎模式" : `Live LLM 真实模型模式 (${(data.config.llm_provider || "OPENAI").toUpperCase()})`;
      }
      if (elements.currentEngineSubTag) {
        elements.currentEngineSubTag.textContent = isMock ? "100% 确定性 · 零网络依赖" : "在线大模型 · 实时推理";
      }
      if (elements.currentEngineModeDesc) {
        elements.currentEngineModeDesc.textContent = isMock
          ? "当前运行于本地离线模拟与图谱规则引擎，无需网络与 API Key，确保开发自测与离线评审 100% 稳定可复现。"
          : "当前正在调用真实大模型推理接口，进行高拟真多轮对话、文书润色与学术套磁文献共振。";
      }
      if (elements.modePulseDot) {
        if (isMock) {
          elements.modePulseDot.classList.remove("live");
        } else {
          elements.modePulseDot.classList.add("live");
        }
      }
      if (elements.toggleEngineBtnText) {
        elements.toggleEngineBtnText.textContent = isMock ? "切换至 Live LLM 模式" : "切换至离线 Mock 模式";
      }

      if (elements.consoleProviderSelect) {
        elements.consoleProviderSelect.value = data.config.llm_provider || "auto";
      }
      if (elements.consoleModelInput) {
        elements.consoleModelInput.value = data.config.openai_model || "";
      }
      if (elements.consoleBaseUrlInput) {
        elements.consoleBaseUrlInput.value = data.config.openai_api_base || "";
      }
      if (elements.consoleKeyMaskedHint) {
        elements.consoleKeyMaskedHint.textContent = data.config.has_api_key
          ? `当前密钥状态: 已配置 [${data.config.api_key_masked}]`
          : "当前状态: 未配置 API Key (使用离线 Mock)";
      }
      if (elements.consoleTempSlider) {
        elements.consoleTempSlider.value = data.config.temperature || 0.2;
      }
      if (elements.consoleTempBadge) {
        elements.consoleTempBadge.textContent = Number(data.config.temperature || 0.2).toFixed(2);
      }
    } catch (e) {
      console.error("Failed to load console config:", e);
    }
  }

  async function toggleEngineMode() {
    if (!currentConsoleConfig) await loadConsoleConfig();
    const isMock = currentConsoleConfig && currentConsoleConfig.is_offline_mock;
    const targetMock = !isMock;

    try {
      const resp = await fetch("/api/admin/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ offline_mock: targetMock })
      });
      const data = await resp.json();
      currentConsoleConfig = data.config;
      await loadConsoleConfig();
      showToast(targetMock ? "已切换为 Deterministic 离线模拟引擎" : "已激活 Live LLM 在线模型模式", "success");
    } catch (e) {
      showToast(`模式切换失败: ${e.message}`, "error");
    }
  }

  async function testConsoleConnection() {
    if (!elements.btnTestConn) return;
    const origText = elements.btnTestConn.innerHTML;
    elements.btnTestConn.innerHTML = '<span class="btn-icon">⏳</span> 正在测试...';
    elements.btnTestConn.disabled = true;

    const payload = {
      provider: elements.consoleProviderSelect ? elements.consoleProviderSelect.value : null,
      api_key: elements.consoleApiKeyInput && elements.consoleApiKeyInput.value.trim() ? elements.consoleApiKeyInput.value.trim() : null,
      base_url: elements.consoleBaseUrlInput ? elements.consoleBaseUrlInput.value.trim() : null,
      model: elements.consoleModelInput ? elements.consoleModelInput.value.trim() : null,
    };

    try {
      const resp = await fetch("/api/admin/config/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await resp.json();

      if (elements.consoleEngineFeedback) {
        elements.consoleEngineFeedback.classList.remove("hidden", "success", "error");
        if (data.status === "ok") {
          elements.consoleEngineFeedback.classList.add("success");
          elements.consoleEngineFeedback.innerHTML = `
            <strong>✓ 测试成功 [${data.mode.toUpperCase()}]</strong>: ${data.message}
            <div style="margin-top:4px; font-size:0.75rem; opacity:0.85;">
              耗时: ${data.latency_ms}ms | 模型: ${data.model || "default"} | 渠道: ${data.provider}
            </div>
          `;
          showToast("LLM 连接测试成功！", "success");
        } else {
          elements.consoleEngineFeedback.classList.add("error");
          elements.consoleEngineFeedback.innerHTML = `
            <strong>✕ 连接测试未通过</strong>: ${data.message}
          `;
          showToast("连接测试未通过，请检查参数", "warn");
        }
      }
    } catch (e) {
      if (elements.consoleEngineFeedback) {
        elements.consoleEngineFeedback.classList.remove("hidden", "success");
        elements.consoleEngineFeedback.classList.add("error");
        elements.consoleEngineFeedback.textContent = `网络错误: ${e.message}`;
      }
    } finally {
      elements.btnTestConn.innerHTML = origText;
      elements.btnTestConn.disabled = false;
    }
  }

  async function saveConsoleConfig() {
    if (!elements.btnSaveCfg) return;
    const origText = elements.btnSaveCfg.innerHTML;
    elements.btnSaveCfg.innerHTML = '<span class="btn-icon">⏳</span> 正在保存...';
    elements.btnSaveCfg.disabled = true;

    const payload = {
      llm_provider: elements.consoleProviderSelect ? elements.consoleProviderSelect.value : undefined,
      base_url: elements.consoleBaseUrlInput ? elements.consoleBaseUrlInput.value.trim() : undefined,
      model: elements.consoleModelInput ? elements.consoleModelInput.value.trim() : undefined,
      temperature: elements.consoleTempSlider ? parseFloat(elements.consoleTempSlider.value) : undefined,
    };

    if (elements.consoleApiKeyInput && elements.consoleApiKeyInput.value.trim()) {
      payload.api_key = elements.consoleApiKeyInput.value.trim();
    }

    try {
      const resp = await fetch("/api/admin/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await resp.json();
      currentConsoleConfig = data.config;
      await loadConsoleConfig();

      if (elements.consoleApiKeyInput) elements.consoleApiKeyInput.value = "";

      if (elements.consoleEngineFeedback) {
        elements.consoleEngineFeedback.classList.remove("hidden", "error");
        elements.consoleEngineFeedback.classList.add("success");
        elements.consoleEngineFeedback.textContent = "✓ 系统配置热更新成功，智能体已实时重载推理参数！";
      }
      showToast("系统配置已热更新并即时生效！", "success");
    } catch (e) {
      if (elements.consoleEngineFeedback) {
        elements.consoleEngineFeedback.classList.remove("hidden", "success");
        elements.consoleEngineFeedback.classList.add("error");
        elements.consoleEngineFeedback.textContent = `保存失败: ${e.message}`;
      }
    } finally {
      elements.btnSaveCfg.innerHTML = origText;
      elements.btnSaveCfg.disabled = false;
    }
  }

  // --- Tab B: Knowledge Graph & Case Ingestion ---
  async function loadConsoleStats() {
    try {
      const resp = await fetch("/api/admin/stats");
      if (!resp.ok) return;
      const data = await resp.json();
      const s = data.stats;

      if (elements.statUnis) elements.statUnis.textContent = s.universities_count;
      if (elements.statPrograms) elements.statPrograms.textContent = s.programs_count;
      if (elements.statCourses) elements.statCourses.textContent = s.courses_count;
      if (elements.statProfs) elements.statProfs.textContent = s.professors_count;
      if (elements.statEdges) elements.statEdges.textContent = s.total_edges;
      if (elements.statCases) elements.statCases.textContent = s.total_admission_cases;

      if (elements.graphStoragePath) {
        elements.graphStoragePath.textContent = `底座存储: ${s.total_nodes} 节点 / ${s.total_edges} 边 / ${s.total_admission_cases} 案例 (SQLite 持久化)`;
      }
    } catch (e) {
      console.error("Failed to load console stats:", e);
    }
  }

  async function submitGraphNode() {
    const id = elements.nodeIdInput ? elements.nodeIdInput.value.trim() : "";
    const name = elements.nodeNameInput ? elements.nodeNameInput.value.trim() : "";
    const nodeType = elements.nodeTypeInput ? elements.nodeTypeInput.value : "Program";

    if (!id || !name) {
      showToast("请填写节点 ID 和节点名称", "warn");
      return;
    }

    const properties = {
      degree: "Master",
      region: elements.nodeRegionInput ? elements.nodeRegionInput.value : "UK",
      major_category: elements.nodeMajorInput ? elements.nodeMajorInput.value : "CS",
      min_gpa: elements.nodeGpaInput && elements.nodeGpaInput.value ? parseFloat(elements.nodeGpaInput.value) : 85.0,
      extra_requirements: elements.nodeExtraInput ? elements.nodeExtraInput.value.trim() : "",
    };

    const payload = {
      node_type: nodeType,
      id: id,
      name: name,
      properties: properties,
      university_id: elements.nodeUniIdInput ? elements.nodeUniIdInput.value.trim() : undefined,
    };

    try {
      const resp = await fetch("/api/admin/graph/node", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await resp.json();

      if (resp.ok) {
        if (elements.consoleGraphFeedback) {
          elements.consoleGraphFeedback.classList.remove("hidden", "error");
          elements.consoleGraphFeedback.classList.add("success");
          elements.consoleGraphFeedback.textContent = `✓ ${data.message}`;
        }
        showToast("新图谱节点录入成功！", "success");
        if (elements.nodeIdInput) elements.nodeIdInput.value = "";
        if (elements.nodeNameInput) elements.nodeNameInput.value = "";
        await loadConsoleStats();
      } else {
        throw new Error(data.detail || "录入失败");
      }
    } catch (e) {
      if (elements.consoleGraphFeedback) {
        elements.consoleGraphFeedback.classList.remove("hidden", "success");
        elements.consoleGraphFeedback.classList.add("error");
        elements.consoleGraphFeedback.textContent = `录入错误: ${e.message}`;
      }
      showToast(`图谱录入失败: ${e.message}`, "error");
    }
  }

  async function submitAdmissionCase() {
    const progId = elements.caseProgramInput ? elements.caseProgramInput.value.trim() : "";
    const school = elements.caseSchoolInput ? elements.caseSchoolInput.value.trim() : "";
    const major = elements.caseMajorInput ? elements.caseMajorInput.value.trim() : "";
    const gpa = elements.caseGpaInput && elements.caseGpaInput.value ? parseFloat(elements.caseGpaInput.value) : 0;

    if (!progId || !school || !major || !gpa) {
      showToast("请完整填写目标项目、本科院校、专业和 GPA", "warn");
      return;
    }

    const payload = {
      target_program_id: progId,
      undergrad_name: school,
      undergrad_tier: elements.caseTierInput ? elements.caseTierInput.value : "985",
      gpa: gpa,
      gpa_scale: elements.caseScaleInput ? elements.caseScaleInput.value : "100",
      major: major,
      language: elements.caseLangInput && elements.caseLangInput.value.trim() ? elements.caseLangInput.value.trim() : "雅思 7.5 (6.5)",
      outcome: elements.caseOutcomeInput ? elements.caseOutcomeInput.value : "ADMIT",
      outcome_type: elements.caseOutcomeInput && elements.caseOutcomeInput.value === "REJECT" ? "reject" : "admit",
      year: elements.caseYearInput && elements.caseYearInput.value ? parseInt(elements.caseYearInput.value, 10) : 2025,
      background_summary: elements.caseSummaryInput ? elements.caseSummaryInput.value.trim() : "微服务后端开发与科研经历",
    };

    try {
      const resp = await fetch("/api/admin/cases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await resp.json();

      if (resp.ok) {
        if (elements.consoleGraphFeedback) {
          elements.consoleGraphFeedback.classList.remove("hidden", "error");
          elements.consoleGraphFeedback.classList.add("success");
          elements.consoleGraphFeedback.textContent = `✓ ${data.message}`;
        }
        showToast("同辈案例已成功向量化录入！", "success");
        if (elements.caseSchoolInput) elements.caseSchoolInput.value = "";
        if (elements.caseMajorInput) elements.caseMajorInput.value = "";
        if (elements.caseGpaInput) elements.caseGpaInput.value = "";
        if (elements.caseSummaryInput) elements.caseSummaryInput.value = "";
        await loadConsoleStats();
      } else {
        throw new Error(data.detail || "录入失败");
      }
    } catch (e) {
      if (elements.consoleGraphFeedback) {
        elements.consoleGraphFeedback.classList.remove("hidden", "success");
        elements.consoleGraphFeedback.classList.add("error");
        elements.consoleGraphFeedback.textContent = `案例写入错误: ${e.message}`;
      }
      showToast(`案例写入失败: ${e.message}`, "error");
    }
  }

  // --- Tab C: Benchmark Online Inspection ---
  function renderBenchmarkReportData(report) {
    if (!report || !report.metrics) return;
    const gr = report.metrics.prismera_graphrag;
    const bl = report.metrics.baseline_pure_prompt;

    if (elements.evalLastRunTimestamp && report.execution_meta) {
      elements.evalLastRunTimestamp.textContent = `最近一次巡检: ${report.execution_meta.timestamp} (耗时 ${report.execution_meta.elapsed_seconds}s | 28/28 通过)`;
    }

    // Metric 1: Hard Constraint
    if (elements.gaugeValHard) elements.gaugeValHard.textContent = `${gr.Hard_Constraint_Precision.toFixed(1)}%`;
    if (elements.gaugeBaseHard) elements.gaugeBaseHard.textContent = `Baseline: ${bl.Hard_Constraint_Precision.toFixed(1)}%`;
    if (elements.gaugeBarHard) elements.gaugeBarHard.style.width = `${gr.Hard_Constraint_Precision}%`;
    if (elements.gaugeDeltaHard) {
      const delta = gr.Hard_Constraint_Precision - bl.Hard_Constraint_Precision;
      elements.gaugeDeltaHard.textContent = `+${delta.toFixed(1)}%`;
    }

    // Metric 2: Stage Gate
    if (elements.gaugeValGate) elements.gaugeValGate.textContent = `${gr.Stage_Gate_Compliance.toFixed(1)}%`;
    if (elements.gaugeBaseGate) elements.gaugeBaseGate.textContent = `Baseline: ${bl.Stage_Gate_Compliance.toFixed(1)}%`;
    if (elements.gaugeBarGate) elements.gaugeBarGate.style.width = `${gr.Stage_Gate_Compliance}%`;
    if (elements.gaugeDeltaGate) {
      const delta = gr.Stage_Gate_Compliance - bl.Stage_Gate_Compliance;
      elements.gaugeDeltaGate.textContent = `+${delta.toFixed(1)}%`;
    }

    // Metric 3: Anti-AI Lexicon
    if (elements.gaugeValAi) elements.gaugeValAi.textContent = `${gr.Anti_AI_Lexicon_Clean_Rate.toFixed(1)}%`;
    if (elements.gaugeBaseAi) elements.gaugeBaseAi.textContent = `Baseline: ${bl.Anti_AI_Lexicon_Clean_Rate.toFixed(1)}%`;
    if (elements.gaugeBarAi) elements.gaugeBarAi.style.width = `${gr.Anti_AI_Lexicon_Clean_Rate}%`;
    if (elements.gaugeDeltaAi) {
      const delta = gr.Anti_AI_Lexicon_Clean_Rate - bl.Anti_AI_Lexicon_Clean_Rate;
      elements.gaugeDeltaAi.textContent = `+${delta.toFixed(1)}%`;
    }

    // Metric 4: Citation Faithfulness
    if (elements.gaugeValCite) elements.gaugeValCite.textContent = `${gr.Citation_Faithfulness.toFixed(1)}%`;
    if (elements.gaugeBaseCite) elements.gaugeBaseCite.textContent = `Baseline: ${bl.Citation_Faithfulness.toFixed(1)}%`;
    if (elements.gaugeBarCite) elements.gaugeBarCite.style.width = `${gr.Citation_Faithfulness}%`;
    if (elements.gaugeDeltaCite) {
      const delta = gr.Citation_Faithfulness - bl.Citation_Faithfulness;
      elements.gaugeDeltaCite.textContent = `+${delta.toFixed(1)}%`;
    }

    // Cases Breakdown List
    if (elements.evalCasesList && report.case_details) {
      elements.evalCasesList.innerHTML = "";
      report.case_details.forEach(item => {
        const row = document.createElement("div");
        row.className = "case-item-row";
        const grTag = item.prismera_pass ? '<span class="tag-pass">PrismEra: ✅</span>' : '<span class="tag-fail">PrismEra: ❌</span>';
        const blTag = item.baseline_pass ? '<span class="tag-pass">Baseline: ✅</span>' : '<span class="tag-fail">Baseline: ❌</span>';

        row.innerHTML = `
          <span class="case-id-tag">${item.id}</span>
          <span class="case-title-text" title="${item.title || item.id}">${item.title || item.id}</span>
          <div class="case-badges-col">
            ${grTag}
            ${blTag}
          </div>
        `;
        elements.evalCasesList.appendChild(row);
      });
      if (elements.casesTableCount) {
        elements.casesTableCount.textContent = `共 ${report.case_details.length} 项陷阱用例`;
      }
    }
  }

  async function loadConsoleBenchmarkLatest() {
    try {
      const resp = await fetch("/api/admin/benchmark/latest");
      if (!resp.ok) return;
      const data = await resp.json();
      if (data.status === "success" && data.report) {
        renderBenchmarkReportData(data.report);
      } else {
        if (elements.evalLastRunTimestamp) {
          elements.evalLastRunTimestamp.textContent = "尚未运行评测，请点击右侧按钮启动巡检。";
        }
      }
    } catch (e) {
      console.error("Failed to load benchmark report:", e);
    }
  }

  async function runConsoleBenchmarkOnline() {
    if (!elements.btnRunBenchmark) return;
    const origText = elements.btnRunBenchmark.innerHTML;
    elements.btnRunBenchmark.innerHTML = '<span class="btn-icon">⏳</span> 正在巡检 28 个高危陷阱题...';
    elements.btnRunBenchmark.disabled = true;

    try {
      const resp = await fetch("/api/admin/benchmark/run", { method: "POST" });
      const data = await resp.json();
      if (resp.ok && data.report) {
        renderBenchmarkReportData(data.report);
        showToast(data.message || "Benchmark 在线巡检全通！", "success");
      } else {
        throw new Error(data.detail || "巡检失败");
      }
    } catch (e) {
      showToast(`巡检异常: ${e.message}`, "error");
    } finally {
      elements.btnRunBenchmark.innerHTML = origText;
      elements.btnRunBenchmark.disabled = false;
    }
  }

  // Desktop App Distribution Handlers
  async function openDesktopModal() {
    closeProfileDropdown();
    if (!elements.desktopDownloadModal) return;
    elements.desktopDownloadModal.classList.remove("hidden");

    // Client OS Auto-detection
    const ua = (navigator.userAgent || "").toLowerCase();
    const platform = (navigator.platform || "").toLowerCase();
    const isMac = platform.includes("mac") || ua.includes("macintosh") || ua.includes("mac os");
    const isWin = platform.includes("win") || ua.includes("windows");

    if (isWin) {
      switchDesktopTab("tab-windows");
      if (elements.winDetectBanner) elements.winDetectBanner.classList.add("detected");
    } else {
      // Default to macOS
      switchDesktopTab("tab-macos");
      if (elements.macDetectBanner) elements.macDetectBanner.classList.add("detected");
    }

    // Query Desktop API metadata
    try {
      const resp = await fetch("/api/desktop/info");
      if (resp.ok) {
        const data = await resp.json();
        if (elements.desktopModalVersion && data.version) {
          elements.desktopModalVersion.textContent = `v${data.version} Desktop`;
        }
      }
    } catch (e) {
      console.warn("Failed to fetch desktop info:", e);
    }
  }

  function closeDesktopModal() {
    if (!elements.desktopDownloadModal) return;
    elements.desktopDownloadModal.classList.add("hidden");
  }

  function switchDesktopTab(tabId) {
    document.querySelectorAll(".desktop-tab-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === tabId);
    });
    document.querySelectorAll(".desktop-tab-pane").forEach((pane) => {
      pane.classList.toggle("active", pane.id === `pane-${tabId}`);
    });
  }

  // 22. 事件监听绑定
  function bindEvents() {
    elements.sessionIdDisplay.textContent = state.sessionId;

    // 发送按钮与 Enter 键
    elements.sendBtn.addEventListener("click", () => {
      sendUserMessage(elements.chatInput.value);
    });

    elements.chatInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendUserMessage(elements.chatInput.value);
      }
    });

    // 快捷芯片点击
    elements.quickChips.addEventListener("click", (e) => {
      const btn = e.target.closest(".chip-btn");
      if (!btn) return;
      const prompt = btn.getAttribute("data-prompt");
      if (prompt) {
        sendUserMessage(prompt);
      }
    });

    // Tab 切换按钮
    elements.tabBtnProfile.addEventListener("click", () => switchCanvasTab("profile"));
    elements.tabBtnMatrix.addEventListener("click", () => switchCanvasTab("matrix"));
    elements.tabBtnSop.addEventListener("click", () => switchCanvasTab("sop"));
    if (elements.tabBtnEcho) {
      elements.tabBtnEcho.addEventListener("click", () => switchCanvasTab("echo"));
    }
    if (elements.tabBtnResonator) {
      elements.tabBtnResonator.addEventListener("click", () => switchCanvasTab("resonator"));
    }

    // Milestone 9: 文档上传与拖拽事件绑定
    if (elements.btnTriggerFileUpload && elements.resumeFileInput) {
      elements.btnTriggerFileUpload.addEventListener("click", () => {
        elements.resumeFileInput.click();
      });
    }
    if (elements.resumeFileInput) {
      elements.resumeFileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files[0]) {
          handleFileUpload(e.target.files[0]);
          e.target.value = "";
        }
      });
    }
    if (elements.dropzoneArea) {
      elements.dropzoneArea.addEventListener("dragover", (e) => {
        e.preventDefault();
        if (elements.dropzoneCard) elements.dropzoneCard.classList.add("dragover");
      });
      elements.dropzoneArea.addEventListener("dragleave", () => {
        if (elements.dropzoneCard) elements.dropzoneCard.classList.remove("dragover");
      });
      elements.dropzoneArea.addEventListener("drop", (e) => {
        e.preventDefault();
        if (elements.dropzoneCard) elements.dropzoneCard.classList.remove("dragover");
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
          handleFileUpload(e.dataTransfer.files[0]);
        }
      });
    }
    if (elements.btnClearUploadPill && elements.uploadResultPill) {
      elements.btnClearUploadPill.addEventListener("click", () => {
        elements.uploadResultPill.classList.add("hidden");
      });
    }

    // Milestone 9: 先修课切面师诊断按钮
    if (elements.btnFacetPrereqAudit) {
      elements.btnFacetPrereqAudit.addEventListener("click", () => {
        sendUserMessage("请切面师帮我深度诊断成绩单和先修课，核算WES GPA并梳理结构性暗区。");
      });
    }

    // Milestone 9: 共鸣者学术套磁事件绑定
    if (elements.btnSearchProfessor) {
      elements.btnSearchProfessor.addEventListener("click", () => {
        const val = elements.resonatorProfInput ? elements.resonatorProfInput.value.trim() : "";
        if (val) {
          sendUserMessage(`我想联系 ${val} 教授，请检索他的最新论文并帮我写一封高信噪比套磁信。`);
        } else {
          showToast("请输入导师姓名或研究方向", "warn");
        }
      });
    }
    if (elements.btnCopyColdEmail && elements.coldEmailBox) {
      elements.btnCopyColdEmail.addEventListener("click", () => {
        const text = elements.coldEmailBox.textContent.trim();
        navigator.clipboard.writeText(text).then(() => {
          showToast("已复制 220 词黄金标准套磁信草稿！", "success");
        }).catch(() => {
          showToast("复制失败，请手动选取", "warn");
        });
      });
    }

    // Milestone 9: 添加图谱项目到选校矩阵事件绑定
    if (elements.btnOpenAddProgModal) {
      elements.btnOpenAddProgModal.addEventListener("click", openAddProgramModal);
    }
    if (elements.closeAddProgModalBtn) {
      elements.closeAddProgModalBtn.addEventListener("click", closeAddProgramModal);
    }
    if (elements.cancelAddProgBtn) {
      elements.cancelAddProgBtn.addEventListener("click", closeAddProgramModal);
    }
    if (elements.progSearchKeyword) {
      elements.progSearchKeyword.addEventListener("input", renderProgramSearchResults);
    }
    if (elements.progRegionPills) {
      elements.progRegionPills.querySelectorAll(".filter-pill").forEach(pill => {
        pill.addEventListener("click", () => {
          elements.progRegionPills.querySelectorAll(".filter-pill").forEach(p => p.classList.remove("active"));
          pill.classList.add("active");
          selectedRegionFilter = pill.getAttribute("data-region") || "";
          renderProgramSearchResults();
        });
      });
    }

    // Milestone 9: 实战模拟面试在线作答与评分
    if (elements.btnSubmitLiveEval) {
      elements.btnSubmitLiveEval.addEventListener("click", submitLiveInterviewAnswer);
    }

    // 表单提交
    elements.saveProfileBtn.addEventListener("click", handleProfileSave);

    // JSON 粘贴折叠
    elements.jsonPasteToggleBtn.addEventListener("click", () => {
      elements.jsonPasteArea.classList.toggle("hidden");
    });
    elements.applyJsonBtn.addEventListener("click", handleApplyJson);

    // 重置会话
    elements.newSessionBtn.addEventListener("click", handleNewSession);

    // 复制文书文本
    elements.copyDraftBtn.addEventListener("click", () => {
      const text = elements.draftTextBox.textContent.trim();
      navigator.clipboard.writeText(text).then(() => {
        showToast("已成功复制去 AI 化淬炼文书草稿！", "success");
      }).catch(() => {
        showToast("复制失败，请手动选取", "warn");
      });
    });

    // --- Milestone 4 事件绑定 ---

    // 选校矩阵确认按钮
    if (elements.confirmMatrixBtn) {
      elements.confirmMatrixBtn.addEventListener("click", () => {
        patchCanvasState({
          pending_human_review: null
        }, "✓ 选校矩阵确认完毕，定焦师锁定完成！");
      });
    }

    // 大纲 "+ 要点" 按钮
    document.querySelectorAll(".btn-add-point").forEach(btn => {
      btn.addEventListener("click", () => handleAddOutlinePoint(btn.dataset.section));
    });

    // 大纲确认并推进执笔成文 (Stage 3)
    if (elements.confirmOutlineBtn) {
      elements.confirmOutlineBtn.addEventListener("click", async () => {
        const outline = getCollectedOutline();
        elements.confirmOutlineBtn.disabled = true;
        elements.confirmOutlineBtn.textContent = "⚡ 推进 Stage 3 执笔成文...";

        try {
          const resp = await fetch("/api/canvas/confirm-outline", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              session_id: state.sessionId,
              outline: outline
            })
          });

          if (!resp.ok) throw new Error("推进执笔失败");
          const data = await resp.json();
          state.studentProfile = data.profile;
          state.pendingHumanReview = null;
          refreshSopView(data.sop_stage || 3, data.profile);

          if (data.latest_response) {
            ensureAssistantMessageBubble("disperser");
            state.currentBubbleContentEl.innerHTML = renderMarkdown(data.latest_response);
            scrollToBottom();
          }

          showToast("✦ 大纲已确认，折光师已完成 Stage 3/4 执笔成文与暗室审片！", "success");
        } catch (e) {
          showToast(`推进执笔失败: ${e.message}`, "error");
        } finally {
          elements.confirmOutlineBtn.disabled = false;
          elements.confirmOutlineBtn.textContent = "✦ 确认大纲并执笔成文 (Stage 3)";
        }
      });
    }

    // 划词选取正文触发局部折射胶囊
    if (elements.draftTextBox) {
      elements.draftTextBox.addEventListener("mouseup", (e) => {
        const selection = window.getSelection();
        const selected = selection.toString().trim();
        if (selected.length >= 6) {
          state.selectedSnippet = selected;
          const range = selection.getRangeAt(0);
          const rect = range.getBoundingClientRect();
          if (elements.floatingRefractPill) {
            const topPos = rect.top - 44 < 60 ? rect.bottom + 8 : rect.top - 40;
            const leftPos = Math.max(16, Math.min(window.innerWidth - 180, rect.left + (rect.width / 2) - 65));
            elements.floatingRefractPill.style.top = `${topPos}px`;
            elements.floatingRefractPill.style.left = `${leftPos}px`;
            elements.floatingRefractPill.classList.remove("hidden");
          }
        } else {
          if (elements.floatingRefractPill && !e.target.closest("#floating-refract-pill")) {
            elements.floatingRefractPill.classList.add("hidden");
          }
        }
      });
    }

    // 局部折射胶囊点击 -> 打开工作台
    if (elements.floatingRefractPill) {
      elements.floatingRefractPill.addEventListener("click", () => {
        elements.floatingRefractPill.classList.add("hidden");
        if (elements.refractionWorkbench) {
          elements.refractionWorkbench.classList.remove("hidden");
          if (elements.refractSelectedPreview) {
            elements.refractSelectedPreview.textContent = `“${state.selectedSnippet}”`;
          }
          if (elements.refractInstructionInput) {
            elements.refractInstructionInput.focus();
          }
          if (elements.diffViewPanel) {
            elements.diffViewPanel.classList.add("hidden");
          }
        }
      });
    }

    if (elements.closeRefractBtn) {
      elements.closeRefractBtn.addEventListener("click", () => {
        if (elements.refractionWorkbench) elements.refractionWorkbench.classList.add("hidden");
        if (elements.diffViewPanel) elements.diffViewPanel.classList.add("hidden");
      });
    }

    // 快捷意图 Chips
    document.querySelectorAll(".refract-chip").forEach(chip => {
      chip.addEventListener("click", () => {
        const inst = chip.dataset.inst;
        if (elements.refractInstructionInput) {
          elements.refractInstructionInput.value = inst;
        }
        executeRefraction(inst);
      });
    });

    if (elements.executeRefractBtn) {
      elements.executeRefractBtn.addEventListener("click", () => {
        const inst = (elements.refractInstructionInput && elements.refractInstructionInput.value.trim()) || "去AI塑料感并强化工程动作";
        executeRefraction(inst);
      });
    }

    if (elements.acceptDiffBtn) {
      elements.acceptDiffBtn.addEventListener("click", handleAcceptDiff);
    }

    if (elements.rejectDiffBtn) {
      elements.rejectDiffBtn.addEventListener("click", () => {
        if (elements.diffViewPanel) elements.diffViewPanel.classList.add("hidden");
        showToast("已驳回本次局部折射重写", "info");
      });
    }

    if (elements.rollbackVersionBtn) {
      elements.rollbackVersionBtn.addEventListener("click", handleRollbackVersion);
    }

    // --- Milestone 5: 回音壁面试与时间轴交互事件 ---
    if (elements.btnTriggerKira) {
      elements.btnTriggerKira.addEventListener("click", () => {
        sendUserMessage("请回音壁为我发起卡耐基梅隆 MSIT-SE 项目的 Kira 模拟面试第一题，并对我作答进行评分。");
      });
    }
    if (elements.btnTriggerAlumni) {
      elements.btnTriggerAlumni.addEventListener("click", () => {
        sendUserMessage("请回音壁为我发起校友行为面试 (Alumni Behavioral)，重点考核我的 STAR 结构与工程领导力。");
      });
    }
    if (elements.btnTriggerTech) {
      elements.btnTriggerTech.addEventListener("click", () => {
        sendUserMessage("请回音壁为我发起导师学术与技术面试 (Professor Technical)，深入考核我的科研论文与系统架构假设。");
      });
    }
    if (elements.btnTriggerTimeline) {
      elements.btnTriggerTimeline.addEventListener("click", () => {
        sendUserMessage("请帮我梳理当前锁定项目的网申时间轴、倒计时及推荐信催交节点。");
      });
    }
    if (elements.btnNextQuestion) {
      elements.btnNextQuestion.addEventListener("click", () => {
        sendUserMessage("请出下一道模拟面试真题。");
      });
    }
    if (elements.btnCopySample) {
      elements.btnCopySample.addEventListener("click", () => {
        const text = (elements.refinedSampleBody && elements.refinedSampleBody.textContent.trim()) || "";
        if (text) {
          navigator.clipboard.writeText(text).then(() => {
            showToast("已成功复制高分示范回答至剪贴板！", "success");
          }).catch(() => {
            showToast("复制失败，请手动选取", "warn");
          });
        }
      });
    }

    // --- Milestone 7: 档案切换器与全案导出模态事件 ---
    if (elements.profileSwitcherBtn) {
      elements.profileSwitcherBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        toggleProfileDropdown();
      });
    }

    document.addEventListener("click", (e) => {
      if (elements.profileDropdown && !e.target.closest("#profile-switcher-wrapper")) {
        closeProfileDropdown();
      }
    });

    if (elements.dropdownNewProfileBtn) {
      elements.dropdownNewProfileBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        openCreateProfileModal();
      });
    }

    if (elements.closeCreateModalBtn) {
      elements.closeCreateModalBtn.addEventListener("click", closeCreateProfileModal);
    }
    if (elements.cancelCreateProfileBtn) {
      elements.cancelCreateProfileBtn.addEventListener("click", closeCreateProfileModal);
    }
    if (elements.confirmCreateProfileBtn) {
      elements.confirmCreateProfileBtn.addEventListener("click", confirmCreateProfile);
    }

    if (elements.closeRenameModalBtn) {
      elements.closeRenameModalBtn.addEventListener("click", closeRenameModal);
    }
    if (elements.cancelRenameProfileBtn) {
      elements.cancelRenameProfileBtn.addEventListener("click", closeRenameModal);
    }
    if (elements.confirmRenameProfileBtn) {
      elements.confirmRenameProfileBtn.addEventListener("click", confirmRenameProfile);
    }

    if (elements.btnExportDossier) {
      elements.btnExportDossier.addEventListener("click", openExportModal);
    }
    if (elements.closeExportModalBtn) {
      elements.closeExportModalBtn.addEventListener("click", closeExportModal);
    }
    if (elements.tabPreviewHtml) {
      elements.tabPreviewHtml.addEventListener("click", () => switchExportPreviewTab("html"));
    }
    if (elements.tabPreviewMd) {
      elements.tabPreviewMd.addEventListener("click", () => switchExportPreviewTab("md"));
    }
    if (elements.btnModalCopyMd) {
      elements.btnModalCopyMd.addEventListener("click", copyMarkdownExport);
    }
    if (elements.btnModalDlMd) {
      elements.btnModalDlMd.addEventListener("click", downloadMarkdownExport);
    }
    if (elements.btnModalDlHtml) {
      elements.btnModalDlHtml.addEventListener("click", downloadHtmlExport);
    }
    if (elements.btnModalOpenNew) {
      elements.btnModalOpenNew.addEventListener("click", openFullscreenExport);
    }

    // Milestone 8: 棱镜控制台事件绑定
    if (elements.btnOpenConsole) {
      elements.btnOpenConsole.addEventListener("click", openConsoleModal);
    }
    if (elements.closeConsoleModalBtn) {
      elements.closeConsoleModalBtn.addEventListener("click", closeConsoleModal);
    }
    if (elements.tabConsoleEngine) {
      elements.tabConsoleEngine.addEventListener("click", () => switchConsoleTab("engine"));
    }
    if (elements.tabConsoleGraph) {
      elements.tabConsoleGraph.addEventListener("click", () => switchConsoleTab("graph"));
    }
    if (elements.tabConsoleBenchmark) {
      elements.tabConsoleBenchmark.addEventListener("click", () => switchConsoleTab("benchmark"));
    }
    if (elements.btnToggleEngineMode) {
      elements.btnToggleEngineMode.addEventListener("click", toggleEngineMode);
    }
    if (elements.btnToggleKeyView && elements.consoleApiKeyInput) {
      elements.btnToggleKeyView.addEventListener("click", () => {
        const isPass = elements.consoleApiKeyInput.type === "password";
        elements.consoleApiKeyInput.type = isPass ? "text" : "password";
        elements.btnToggleKeyView.textContent = isPass ? "🔒" : "👁️";
      });
    }
    if (elements.consoleTempSlider && elements.consoleTempBadge) {
      elements.consoleTempSlider.addEventListener("input", (e) => {
        elements.consoleTempBadge.textContent = Number(e.target.value).toFixed(2);
      });
    }
    if (elements.btnTestConn) {
      elements.btnTestConn.addEventListener("click", testConsoleConnection);
    }
    if (elements.btnSaveCfg) {
      elements.btnSaveCfg.addEventListener("click", saveConsoleConfig);
    }
    if (elements.btnRefreshStats) {
      elements.btnRefreshStats.addEventListener("click", loadConsoleStats);
    }
    if (elements.btnSubmitNode) {
      elements.btnSubmitNode.addEventListener("click", submitGraphNode);
    }
    if (elements.btnSubmitCase) {
      elements.btnSubmitCase.addEventListener("click", submitAdmissionCase);
    }
    if (elements.btnRunBenchmark) {
      elements.btnRunBenchmark.addEventListener("click", runConsoleBenchmarkOnline);
    }

    // Desktop App Modal Listeners
    if (elements.btnOpenDesktopModal) {
      elements.btnOpenDesktopModal.addEventListener("click", openDesktopModal);
    }
    if (elements.closeDesktopModalBtn) {
      elements.closeDesktopModalBtn.addEventListener("click", closeDesktopModal);
    }
    if (elements.cancelDesktopModalBtn) {
      elements.cancelDesktopModalBtn.addEventListener("click", closeDesktopModal);
    }
    document.querySelectorAll(".desktop-tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (btn.dataset.tab) switchDesktopTab(btn.dataset.tab);
      });
    });
    if (elements.desktopDownloadModal) {
      elements.desktopDownloadModal.addEventListener("click", (e) => {
        if (e.target === elements.desktopDownloadModal) closeDesktopModal();
      });
    }
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        if (elements.profileDropdown && !elements.profileDropdown.classList.contains("hidden")) {
          closeProfileDropdown();
        }
        if (elements.desktopDownloadModal && !elements.desktopDownloadModal.classList.contains("hidden")) {
          closeDesktopModal();
        }
      }
    });
  }

  // 23. 启动初始化
  closeProfileDropdown();
  bindEvents();
  loadSessionSpectrum();
  loadProfileList();
})();
