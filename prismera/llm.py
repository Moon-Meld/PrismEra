"""PrismEra Dual-Mode LLM Engine.

Provides seamless switching between:
  1. Offline Deterministic Mock Mode (100% offline, zero network, for pytest and local demo)
  2. Real LLM Inference (OpenAI API / Claude / DeepSeek / local Ollama)
with strict Pydantic Structured Output enforcement and zero format error guarantees.
"""

from __future__ import annotations
import json
import os
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel, ValidationError

from prismera.config import (
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_API_BASE,
    OPENAI_MODEL,
    ANTHROPIC_API_KEY,
    ANTHROPIC_BASE_URL,
    ANTHROPIC_MODEL,
    DEEPSEEK_API_KEY,
    DEEPSEEK_API_BASE,
    DEEPSEEK_MODEL,
    OLLAMA_API_BASE,
    OLLAMA_MODEL,
    DEFAULT_TEMPERATURE,
    is_offline_mock,
)
from prismera.state import LuminaryDecision, StudentSpectrumProfile
from prismera.prompts.luminary import LUMINARY_SYSTEM_PROMPT

T = TypeVar("T", bound=BaseModel)


def _clean_json_markdown(text: str) -> str:
    """Strip markdown code fence wrappers from JSON string."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _extract_student_attributes_heuristic(text: str, current_profile: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic extractor for student hard credentials."""
    updates: Dict[str, Any] = {}

    if "985" in text:
        updates["undergrad_tier"] = "985"
    elif "211" in text:
        updates["undergrad_tier"] = "211"
    elif "双非" in text:
        updates["undergrad_tier"] = "双非一本"
    elif "海本" in text or "美本" in text or "英本" in text:
        updates["undergrad_tier"] = "海本"

    for school in [
        "清华", "北大", "浙江大学", "浙大", "复旦", "上海交大", "上交",
        "南京大学", "南大", "华中科技大学", "华科", "武汉大学", "武大",
        "哈工大", "北京航空航天大学", "北航", "同济大学", "同济",
        "西安交通大学", "西交", "东南大学", "中南大学", "中山大学",
        "电子科技大学", "成电", "北京邮电大学", "北邮", "西安电子科技大学", "西电"
    ]:
        if school in text:
            updates["undergrad_name"] = school
            if "undergrad_tier" not in updates and not current_profile.get("undergrad_tier"):
                updates["undergrad_tier"] = "985" if school not in ["北邮", "西电"] else "211"
            break

    for m in ["计算机", "软件工程", "计科", "cs", "computer science"]:
        if m in text.lower():
            updates["major"] = "计算机科学与技术 (CS)"
            break
    for m in ["数据科学", "ds", "data science"]:
        if m in text.lower():
            updates["major"] = "数据科学 (DS)"
            break
    for m in ["商业分析", "ba", "business analytics"]:
        if m in text.lower():
            updates["major"] = "商业分析 (BA)"
            break

    # 匹配 100 分制 GPA (如: 均分88.5, 均分 88.5, 均分是88.5, 88.5分, 88.5/100)
    gpa_match = re.search(r"(?:均分|gpa|绩点)\s*(?:为|是|[:：])?\s*(\d{2}(?:\.\d+)?)|(\d{2}(?:\.\d+)?)\s*(?:分|/100|均分)", text, re.IGNORECASE)
    if gpa_match:
        val = gpa_match.group(1) or gpa_match.group(2)
        if val:
            updates["gpa_raw"] = f"{val}/100"
    else:
        # 匹配 4.0 分制 (如: GPA 3.8, GPA是3.85, 3.8/4.0, 绩点3.7)
        gpa_4_match = re.search(r"(?:gpa|绩点)\s*(?:为|是|[:：])?\s*([34]\.\d{1,2})|([34]\.\d{1,2})\s*(?:/4\.0|gpa)", text, re.IGNORECASE)
        if gpa_4_match:
            val = gpa_4_match.group(1) or gpa_4_match.group(2)
            if val:
                updates["gpa_raw"] = f"{val}/4.0"

    ielts_match = re.search(r"雅思(?:总分|成绩|分数)?\s*[:：]?\s*([6789](?:\.[05])?)", text)
    if ielts_match:
        lang_dict = dict(current_profile.get("language_scores") or {})
        lang_dict["IELTS_total"] = float(ielts_match.group(1))
        sub_match = re.search(r"口语(?:小分|成绩|分数)?\s*[:：]?\s*([56789](?:\.[05])?)", text)
        if sub_match:
            lang_dict["speaking"] = float(sub_match.group(1))
        updates["language_scores"] = lang_dict

    toefl_match = re.search(r"托福(?:总分|成绩|分数)?\s*[:：]?\s*(\d{2,3})", text)
    if toefl_match:
        lang_dict = dict(current_profile.get("language_scores") or {})
        lang_dict["TOEFL_total"] = float(toefl_match.group(1))
        sub_match = re.search(r"口语(?:小分|成绩|分数)?\s*[:：]?\s*(\d{1,2})", text)
        if sub_match:
            lang_dict["speaking"] = float(sub_match.group(1))
        updates["language_scores"] = lang_dict

    regions = []
    if any(k in text for k in ["美国", "美研", "US", "USA"]):
        regions.append("US")
    if any(k in text for k in ["英国", "英研", "UK"]):
        regions.append("UK")
    if any(k in text for k in ["香港", "港校", "HK"]):
        regions.append("HK")
    if any(k in text for k in ["新加坡", "新二", "SG"]):
        regions.append("SG")
    if regions:
        current_regions = set(current_profile.get("target_regions") or [])
        current_regions.update(regions)
        updates["target_regions"] = list(current_regions)

    target_m = []
    if any(k in text.lower() for k in ["cs", "计算机", "转码", "软件工程"]):
        target_m.append("CS")
    if any(k in text.lower() for k in ["ds", "数据科学"]):
        target_m.append("DS")
    if any(k in text.lower() for k in ["ba", "商业分析"]):
        target_m.append("BA")
    if target_m:
        current_m = set(current_profile.get("target_majors") or [])
        current_m.update(target_m)
        updates["target_majors"] = list(current_m)

    return updates


class BaseLLM(ABC):
    """Abstract interface for PrismEra LLM providers."""

    is_mock: bool = False

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        **kwargs,
    ) -> str:
        """Generate unstructured text completion."""
        pass

    @abstractmethod
    def generate_structured(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[T],
        temperature: Optional[float] = None,
        **kwargs,
    ) -> T:
        """Generate validated Pydantic structured output with zero format errors."""
        pass


class MockLLM(BaseLLM):
    """Offline deterministic mock LLM for testing and local demo without API keys."""

    is_mock: bool = True

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        **kwargs,
    ) -> str:
        last_msg = messages[-1]["content"] if messages else ""
        return f"[MockLLM Output for: {last_msg[:50]}...]"

    def generate_structured(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[T],
        temperature: Optional[float] = None,
        **kwargs,
    ) -> T:
        if response_model is LuminaryDecision:
            return self._mock_luminary_decision(messages, kwargs.get("student_profile", {}))  # type: ignore

        # Generic Pydantic model fallback
        try:
            return response_model()
        except ValidationError:
            # Construct with minimal default values
            schema = response_model.model_json_schema()
            defaults = {}
            for prop, details in schema.get("properties", {}).items():
                if "default" in details:
                    defaults[prop] = details["default"]
                elif details.get("type") == "string":
                    defaults[prop] = ""
                elif details.get("type") == "array":
                    defaults[prop] = []
                elif details.get("type") == "object":
                    defaults[prop] = {}
                elif details.get("type") in ["integer", "number"]:
                    defaults[prop] = 0
                elif details.get("type") == "boolean":
                    defaults[prop] = False
            return response_model.model_validate(defaults)

    def _mock_luminary_decision(
        self, messages: List[Dict[str, str]], current_profile: Dict[str, Any]
    ) -> LuminaryDecision:
        last_user_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "")
                break

        updates = _extract_student_attributes_heuristic(last_user_msg, current_profile)
        merged = dict(current_profile)
        merged.update(updates)

        user_query = last_user_msg.lower()

        locus_keywords = ["选校", "定位", "定校", "定焦", "能申", "录取概率", "冲刺", "择校", "保底", "list"]
        is_asking_locus = any(kw in user_query for kw in locus_keywords)
        if any(neg in user_query for neg in ["定校很有底", "选校很有底", "先不定校", "不用选校", "已经定校"]):
            is_asking_locus = False

        is_asking_facet = any(kw in user_query for kw in ["切面", "成绩单", "gpa", "换算", "背景提升", "诊断", "先修课", "补课", "跨考", "暗区"])
        is_asking_disperser = any(kw in user_query for kw in ["折光", "文书", "sop", "ps", "个人陈述", "简历", "cv", "故事", "润色", "写作", "大纲"])
        is_asking_resonator = any(kw in user_query for kw in ["共鸣", "套磁", "导师", "教授", "论文", "phd", "博士", "科研", "邮件", "rp", "cold email"])
        is_asking_echo = any(kw in user_query for kw in ["回音", "echo", "面试", "面经", "模拟面", "kira", "校友面", "机面", "技术面", "学术面", "网申", "时间轴", "timeline", "deadline", "截止日期", "催交", "清单", "材料清单", "护航"])

        if is_asking_echo:
            is_asking_locus = False

        has_tier = bool(merged.get("undergrad_tier") or merged.get("undergrad_name"))
        has_gpa = bool(merged.get("gpa_raw"))
        has_major = bool(merged_profile_major := merged.get("major"))
        has_target = bool(merged.get("target_regions") and merged.get("target_majors"))
        all_baseline_ready = has_tier and has_gpa and has_major and has_target

        # Context continuation
        last_assistant_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                last_assistant_msg = msg.get("content", "")
                break

        prev_decision = current_profile.get("prev_routing_decision")
        if prev_decision == "ASK_FOR_CLARIFICATION" and all_baseline_ready and not (is_asking_facet or is_asking_disperser or is_asking_resonator or is_asking_echo):
            is_asking_locus = True

        is_continuing_sop = (
            ("折光师" in last_assistant_msg or "SOP" in last_assistant_msg or current_profile.get("sop_stage", 1) in [1, 2, 3])
            and not (is_asking_locus or is_asking_facet or is_asking_resonator or is_asking_echo)
            and (len(last_user_msg) > 30 or "确认" in user_query or "大纲" in user_query)
        )
        if is_continuing_sop:
            is_asking_disperser = True

        if is_asking_facet:
            return LuminaryDecision(
                luminary_thought="用户提出背景评估或课程比对诉求，委派切面师 (prism_facet) 测定优势切面与结构性暗区。",
                state_updates=updates,
                routing_decision="DELEGATE_TO_AGENT",
                target_agent_id="prism_facet",
                task_briefing="对学生成绩单及先修课进行图谱诊断，输出高光切面、暗区及打磨路线图。",
                message_to_user=None,
            )

        if is_asking_locus:
            missing_fields = []
            if not has_tier:
                missing_fields.append("本科院校（名称或层级，如 985/211/双非/海本）")
            if not has_gpa:
                missing_fields.append("当前均分或GPA（如 86/100 或 3.6/4.0）")
            if not has_major:
                missing_fields.append("当前本科所学专业")
            if not has_target:
                missing_fields.append("目标申请地区（美/英/港/新）与期望专业方向（如 CS/DS/BA）")

            if missing_fields:
                message = (
                    "为了在万千学府中为你锁定不失真的落点焦距，定焦师（The Locus）需要几组核心基准参数进行硬核剪枝。\n\n"
                    "请告诉我：\n" +
                    "\n".join(f"{i+1}. 你的{field}" for i, field in enumerate(missing_fields[:3])) +
                    "\n\n只需轻点回复，光学阵列便会立刻为你校准全球学府坐标。"
                )
                return LuminaryDecision(
                    luminary_thought=f"用户请求选校定位，但核心硬指标缺失: {', '.join(missing_fields)}。遵循调度铁律第一条，执行前置校准拦截。",
                    state_updates=updates,
                    routing_decision="ASK_FOR_CLARIFICATION",
                    target_agent_id=None,
                    task_briefing=None,
                    message_to_user=message,
                )
            else:
                return LuminaryDecision(
                    luminary_thought="四项基准硬指标均已校准完备，正式委派定焦师 (prism_locus) 调用图谱与案例库定焦。",
                    state_updates=updates,
                    routing_decision="DELEGATE_TO_AGENT",
                    target_agent_id="prism_locus",
                    task_briefing="请依托全球留学知识图谱与同辈案例库，执行三步定焦并输出三维光谱定档矩阵。",
                    message_to_user=None,
                )

        if is_asking_disperser:
            return LuminaryDecision(
                luminary_thought="用户进入文书共创阶段，委派折光师 (prism_disperser) 启动四阶状态机深度挖掘独家叙事。",
                state_updates=updates,
                routing_decision="DELEGATE_TO_AGENT",
                target_agent_id="prism_disperser",
                task_briefing="启动 Stage 1 苏格拉底访谈，提出具有穿透力的转折点与技术细节追问，严禁直接生成完整初稿。",
                message_to_user=None,
            )

        if is_asking_resonator:
            return LuminaryDecision(
                luminary_thought="用户咨询学术套磁与导师联系，委派共鸣者 (prism_resonator) 检索论文瓶颈与招生动态。",
                state_updates=updates,
                routing_decision="DELEGATE_TO_AGENT",
                target_agent_id="prism_resonator",
                task_briefing="寻找导师论文与学生过往经历的学术共振频率，打造 220 词高信噪比套磁信。",
                message_to_user=None,
            )

        if is_asking_echo:
            return LuminaryDecision(
                luminary_thought="用户提出模拟面试问答或网申截止时间轴诉求，委派回音壁 (prism_echo) 提供全真靶向模拟面试与网申倒计时护航。",
                state_updates=updates,
                routing_decision="DELEGATE_TO_AGENT",
                target_agent_id="prism_echo",
                task_briefing="调阅真实面经题库与截止时间节点，开展限时多维问答评估并生成精确网申倒计时与材料核验清单。",
                message_to_user=None,
            )

        message = (
            "我是 **PrismEra（棱镜纪）** 的中枢主控——**【司光者 · The Luminary】**。\n\n"
            "整座光学阵列已为你校准就绪：\n"
            "- 想要诊断成绩单切面与先修课？唤起 **【切面师】**；\n"
            "- 想要依托知识图谱硬核定校？告诉我们基准指标，**【定焦师】** 为你精确投射；\n"
            "- 想要雕琢文书独家叙事？**【折光师】** 与你开启苏格拉底式故事挖掘；\n"
            "- 想要与海外顶尖学者共振？**【共鸣者】** 为你检索最新文献并定制高回复率邮件；\n"
            "- 想要全真模拟面试与网申时间轴护航？**【回音壁】** 为你靶向出题打分并排定倒计时看板。\n\n"
            "告诉我你目前的学术背景或正在思索的问题，我们即刻启程。"
        )
        return LuminaryDecision(
            luminary_thought="用户尚未提出特定单向需求，司光者以温和智性语调进行承接，指引光学阵列的职能。",
            state_updates=updates,
            routing_decision="DIRECT_ANSWER",
            target_agent_id=None,
            task_briefing=None,
            message_to_user=message,
        )


class OpenAILikeLLM(BaseLLM):
    """OpenAI API and compatible providers (DeepSeek, Ollama, vLLM, etc.)."""

    is_mock: bool = False

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: str = "gpt-4o",
        temperature: float = DEFAULT_TEMPERATURE,
        timeout: float = 60.0,
    ):
        self.api_key = api_key or "sk-no-key-required"
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        **kwargs,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def generate_structured(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[T],
        temperature: Optional[float] = None,
        **kwargs,
    ) -> T:
        schema = response_model.model_json_schema()
        schema_json = json.dumps(schema, ensure_ascii=False)

        system_instruction = (
            f"You MUST reply with a VALID JSON object adhering strictly to this JSON Schema:\n{schema_json}\n"
            "Do NOT output any markdown commentary outside the JSON."
        )

        structured_messages = list(messages)
        # Inject JSON schema requirement into system prompt or append as system message
        if structured_messages and structured_messages[0]["role"] == "system":
            first_msg = structured_messages[0].copy()
            first_msg["content"] = f"{first_msg['content']}\n\n{system_instruction}"
            structured_messages[0] = first_msg
        else:
            structured_messages.insert(0, {"role": "system", "content": system_instruction})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": structured_messages,
            "temperature": self.temperature if temperature is None else temperature,
            "response_format": {"type": "json_object"},
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]

        clean_json = _clean_json_markdown(content)
        try:
            return response_model.model_validate_json(clean_json)
        except ValidationError:
            # If parsing fails, try one repair attempt
            repair_prompt = [
                {"role": "system", "content": f"Fix this JSON to match the schema strictly:\n{schema_json}"},
                {"role": "user", "content": clean_json},
            ]
            repaired_content = self.generate(repair_prompt, temperature=0.0)
            return response_model.model_validate_json(_clean_json_markdown(repaired_content))


class AnthropicLLM(BaseLLM):
    """Anthropic Claude API client."""

    is_mock: bool = False

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = DEFAULT_TEMPERATURE,
        timeout: float = 60.0,
    ):
        self.api_key = api_key
        self.base_url = (base_url or "https://api.anthropic.com").rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        **kwargs,
    ) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        system_content = ""
        claude_msgs = []
        for m in messages:
            if m["role"] == "system":
                system_content += m["content"] + "\n"
            else:
                claude_msgs.append({"role": m["role"], "content": m["content"]})

        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": claude_msgs,
            "temperature": self.temperature if temperature is None else temperature,
        }
        if system_content.strip():
            payload["system"] = system_content.strip()

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.base_url}/v1/messages", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]

    def generate_structured(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[T],
        temperature: Optional[float] = None,
        **kwargs,
    ) -> T:
        schema = response_model.model_json_schema()
        schema_json = json.dumps(schema, ensure_ascii=False)
        system_instruction = (
            f"You MUST reply with a VALID JSON object adhering strictly to this JSON Schema:\n{schema_json}\n"
            "Do NOT output markdown commentary or code block markers outside the JSON."
        )

        mod_messages = [{"role": "system", "content": system_instruction}] + list(messages)
        content = self.generate(mod_messages, temperature=temperature)
        clean_json = _clean_json_markdown(content)
        return response_model.model_validate_json(clean_json)


def get_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
) -> BaseLLM:
    """Factory creating the appropriate LLM client based on configuration.

    Guarantees deterministic MockLLM when offline or when no API keys are present.
    """
    import prismera.config as cfg
    chosen_provider = (provider or cfg.LLM_PROVIDER).strip().lower()

    if chosen_provider == "mock":
        return MockLLM()
    if provider is None and cfg.is_offline_mock():
        return MockLLM()

    temp = cfg.DEFAULT_TEMPERATURE if temperature is None else temperature

    if chosen_provider in ["claude", "anthropic"]:
        return AnthropicLLM(
            api_key=cfg.ANTHROPIC_API_KEY,
            base_url=cfg.ANTHROPIC_BASE_URL,
            model=model or cfg.ANTHROPIC_MODEL,
            temperature=temp,
        )

    if chosen_provider == "deepseek":
        return OpenAILikeLLM(
            api_key=cfg.DEEPSEEK_API_KEY or cfg.OPENAI_API_KEY,
            base_url=cfg.DEEPSEEK_API_BASE,
            model=model or cfg.DEEPSEEK_MODEL,
            temperature=temp,
        )

    if chosen_provider == "ollama":
        return OpenAILikeLLM(
            api_key="ollama",
            base_url=cfg.OLLAMA_API_BASE,
            model=model or cfg.OLLAMA_MODEL,
            temperature=temp,
        )

    if chosen_provider in ["vllm", "lora", "local_lora"]:
        return OpenAILikeLLM(
            api_key=os.getenv("LORA_API_KEY", "EMPTY"),
            base_url=cfg.LORA_API_BASE,
            model=model or cfg.LORA_MODEL,
            temperature=temp,
        )

    # Default to OpenAI-compatible
    return OpenAILikeLLM(
        api_key=cfg.OPENAI_API_KEY,
        base_url=cfg.OPENAI_API_BASE or "https://api.openai.com/v1",
        model=model or cfg.OPENAI_MODEL,
        temperature=temp,
    )


def call_luminary_structured(
    messages: List[Dict[str, str]],
    student_profile: StudentSpectrumProfile,
    llm: Optional[BaseLLM] = None,
) -> LuminaryDecision:
    """Call Luminary decision routing with strict Pydantic Structured Output.

    Guarantees zero format errors. If in real LLM mode and the API fails,
    it falls back gracefully to deterministic rule-based output without crashing.
    """
    active_llm = llm or get_llm()

    # Prepare formatted prompt
    profile_json = json.dumps(student_profile, ensure_ascii=False, indent=2)
    system_prompt = LUMINARY_SYSTEM_PROMPT.replace("{student_profile_json}", profile_json)

    full_messages = [{"role": "system", "content": system_prompt}] + messages

    try:
        decision = active_llm.generate_structured(
            messages=full_messages,
            response_model=LuminaryDecision,
            student_profile=student_profile,
        )
        return decision
    except Exception as e:
        # Fallback to deterministic MockLLM to guarantee graph continuity
        mock_fallback = MockLLM()
        return mock_fallback.generate_structured(
            messages=full_messages,
            response_model=LuminaryDecision,
            student_profile=student_profile,
        )
