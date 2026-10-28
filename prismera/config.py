"""Configuration settings for PrismEra."""

import os
from dotenv import load_dotenv

load_dotenv()

# LLM Provider settings: "auto", "mock", "openai", "deepseek", "claude", "ollama"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").strip().lower()

# OpenAI / OpenAI-compatible settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", os.getenv("OPENAI_BASE_URL", ""))
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Anthropic / Claude settings
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

# DeepSeek settings
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# Local Ollama settings
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Local Fine-Tuned LoRA / vLLM settings
LORA_API_BASE = os.getenv("LORA_API_BASE", os.getenv("VLLM_API_BASE", "http://localhost:8000/v1"))
LORA_MODEL = os.getenv("LORA_MODEL", "qwen2.5-7b-prismera-lora")

# Global generation parameters
DEFAULT_TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))

# Database credentials
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


def is_offline_mock() -> bool:
    """Check if PrismEra should operate in offline deterministic Mock mode.

    Returns True if:
      - LLM_PROVIDER is explicitly set to 'mock'
      - In 'auto' mode and no valid API Key or local endpoint is configured.
    """
    provider = LLM_PROVIDER
    if provider == "mock":
        return True

    if provider in ["ollama", "vllm", "lora", "local_lora"]:
        return False

    if provider in ["deepseek"]:
        return not bool(DEEPSEEK_API_KEY or OPENAI_API_KEY)

    if provider in ["claude", "anthropic"]:
        return not bool(ANTHROPIC_API_KEY)

    if provider == "openai":
        return not bool(OPENAI_API_KEY)

    # In 'auto' mode:
    # 1. Check Anthropic
    if ANTHROPIC_API_KEY:
        return False
    # 2. Check DeepSeek
    if DEEPSEEK_API_KEY:
        return False
    # 3. Check OpenAI / OpenAI-compatible
    if OPENAI_API_KEY:
        return False
    # 4. Check local Ollama or custom local endpoint
    if OPENAI_API_BASE and ("localhost" in OPENAI_API_BASE or "127.0.0.1" in OPENAI_API_BASE):
        return False

    return True


def get_current_config() -> dict:
    """Return dictionary of current LLM and system configuration."""
    global LLM_PROVIDER, OPENAI_API_KEY, OPENAI_API_BASE, OPENAI_MODEL
    global ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_MODEL
    global DEEPSEEK_API_KEY, DEEPSEEK_API_BASE, DEEPSEEK_MODEL
    global OLLAMA_API_BASE, OLLAMA_MODEL, LORA_API_BASE, LORA_MODEL, DEFAULT_TEMPERATURE

    active_key = ""
    if LLM_PROVIDER in ["openai", "auto"]:
        active_key = OPENAI_API_KEY
    elif LLM_PROVIDER == "deepseek":
        active_key = DEEPSEEK_API_KEY or OPENAI_API_KEY
    elif LLM_PROVIDER in ["claude", "anthropic"]:
        active_key = ANTHROPIC_API_KEY

    masked_key = ""
    if active_key:
        if len(active_key) > 8:
            masked_key = f"{active_key[:3]}...{active_key[-4:]}"
        else:
            masked_key = "***"

    return {
        "llm_provider": LLM_PROVIDER,
        "is_offline_mock": is_offline_mock(),
        "has_api_key": bool(active_key),
        "api_key_masked": masked_key,
        "openai_api_base": OPENAI_API_BASE,
        "openai_model": OPENAI_MODEL,
        "deepseek_api_base": DEEPSEEK_API_BASE,
        "deepseek_model": DEEPSEEK_MODEL,
        "anthropic_model": ANTHROPIC_MODEL,
        "ollama_api_base": OLLAMA_API_BASE,
        "ollama_model": OLLAMA_MODEL,
        "lora_api_base": LORA_API_BASE,
        "lora_model": LORA_MODEL,
        "temperature": DEFAULT_TEMPERATURE,
    }


def update_llm_config(
    provider: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    offline_mock: bool | None = None,
) -> dict:
    """Hot-update LLM and runtime configuration parameters."""
    global LLM_PROVIDER, OPENAI_API_KEY, OPENAI_API_BASE, OPENAI_MODEL
    global ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_MODEL
    global DEEPSEEK_API_KEY, DEEPSEEK_API_BASE, DEEPSEEK_MODEL
    global OLLAMA_API_BASE, OLLAMA_MODEL, LORA_API_BASE, LORA_MODEL, DEFAULT_TEMPERATURE

    if offline_mock is not None:
        if offline_mock:
            LLM_PROVIDER = "mock"
            os.environ["LLM_PROVIDER"] = "mock"
        else:
            if LLM_PROVIDER == "mock":
                LLM_PROVIDER = "auto"
                os.environ["LLM_PROVIDER"] = "auto"

    if provider:
        p = provider.strip().lower()
        LLM_PROVIDER = p
        os.environ["LLM_PROVIDER"] = p

    if api_key is not None:
        if LLM_PROVIDER == "deepseek":
            DEEPSEEK_API_KEY = api_key
            os.environ["DEEPSEEK_API_KEY"] = api_key
        elif LLM_PROVIDER in ["claude", "anthropic"]:
            ANTHROPIC_API_KEY = api_key
            os.environ["ANTHROPIC_API_KEY"] = api_key
        else:
            OPENAI_API_KEY = api_key
            os.environ["OPENAI_API_KEY"] = api_key

    if base_url is not None:
        if LLM_PROVIDER == "deepseek":
            DEEPSEEK_API_BASE = base_url
            os.environ["DEEPSEEK_API_BASE"] = base_url
        elif LLM_PROVIDER in ["claude", "anthropic"]:
            ANTHROPIC_BASE_URL = base_url
            os.environ["ANTHROPIC_BASE_URL"] = base_url
        elif LLM_PROVIDER == "ollama":
            OLLAMA_API_BASE = base_url
            os.environ["OLLAMA_API_BASE"] = base_url
        elif LLM_PROVIDER in ["vllm", "lora", "local_lora"]:
            LORA_API_BASE = base_url
            os.environ["LORA_API_BASE"] = base_url
        else:
            OPENAI_API_BASE = base_url
            os.environ["OPENAI_API_BASE"] = base_url

    if model is not None:
        if LLM_PROVIDER == "deepseek":
            DEEPSEEK_MODEL = model
            os.environ["DEEPSEEK_MODEL"] = model
        elif LLM_PROVIDER in ["claude", "anthropic"]:
            ANTHROPIC_MODEL = model
            os.environ["ANTHROPIC_MODEL"] = model
        elif LLM_PROVIDER == "ollama":
            OLLAMA_MODEL = model
            os.environ["OLLAMA_MODEL"] = model
        elif LLM_PROVIDER in ["vllm", "lora", "local_lora"]:
            LORA_MODEL = model
            os.environ["LORA_MODEL"] = model
        else:
            OPENAI_MODEL = model
            os.environ["OPENAI_MODEL"] = model

    if temperature is not None:
        DEFAULT_TEMPERATURE = float(temperature)
        os.environ["TEMPERATURE"] = str(temperature)

    return get_current_config()
