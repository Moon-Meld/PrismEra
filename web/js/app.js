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
    viewProfile: document.getElementById("view-profile"),
    viewMatrix: document.getElementById("view-matrix"),
    viewSop: document.getElementById("view-sop"),
    viewEcho: document.getElementById("view-echo"),

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

    // Matrix View Elements (Milestone 4 HITL)
    matrixBanner: document.getElementById("matrix-banner"),
    matrixOverviewText: document.getElementById("matrix-overview-text"),
    matrixCountBadge: document.getElementById("matrix-count-badge"),
    locusHitlBanner: document.getElementById("locus-hitl-banner"),
    confirmMatrixBtn: document.getElementById("confirm-matrix-btn"),
    reachCardsContainer: document.getElementById("reach-cards-container"),
    matchCardsContainer: document.getElementById("match-cards-container"),
    safetyCardsContainer: document.getElementById("safety-cards-container"),

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
    [elements.tabBtnProfile, elements.tabBtnMatrix, elements.tabBtnSop, elements.tabBtnEcho].forEach(t => t && t.classList.remove("active"));
    [elements.viewProfile, elements.viewMatrix, elements.viewSop, elements.viewEcho].forEach(v => v && v.classList.remove("active"));

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

        item.querySelector(".item-main").addEventListener("click", () => {
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
    state.sessionId = targetSessionId;
    localStorage.setItem("prismera_session_id", targetSessionId);
    if (elements.sessionIdDisplay) {
      elements.sessionIdDisplay.textContent = targetSessionId;
    }
    if (elements.profileDropdown) {
      elements.profileDropdown.classList.add("hidden");
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
    if (elements.profileDropdown) {
      elements.profileDropdown.classList.add("hidden");
    }
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
            elements.floatingRefractPill.style.top = `${rect.top + window.scrollY - 38}px`;
            elements.floatingRefractPill.style.left = `${rect.left + window.scrollX + (rect.width / 2) - 60}px`;
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
        if (elements.profileDropdown) {
          elements.profileDropdown.classList.toggle("hidden");
          if (!elements.profileDropdown.classList.contains("hidden")) {
            loadProfileList();
          }
        }
      });
    }

    document.addEventListener("click", (e) => {
      if (elements.profileDropdown && !e.target.closest("#profile-switcher-wrapper")) {
        elements.profileDropdown.classList.add("hidden");
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
  }

  // 23. 启动初始化
  bindEvents();
  loadSessionSpectrum();
  loadProfileList();
})();
