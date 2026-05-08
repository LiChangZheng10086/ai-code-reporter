from langchain_openai import ChatOpenAI
from app.config import settings


def get_llm(temperature: float = 0.1):
    if settings.llm_provider == "ollama":
        return ChatOpenAI(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            api_key="ollama",
            temperature=temperature,
        )
    # Default: DeepSeek
    return ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url="https://api.deepseek.com/v1",
        temperature=temperature,
    )
