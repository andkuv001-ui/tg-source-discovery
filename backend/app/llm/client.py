from openai import AsyncOpenAI
from app.config import get_settings

settings = get_settings()

llm_client = AsyncOpenAI(
    base_url=settings.routerai_base_url,
    api_key=settings.routerai_api_key,
)


async def chat_completion(messages: list[dict], response_format: dict | None = None, temperature: float = 0.3) -> str:
    kwargs = {"model": settings.routerai_model, "messages": messages, "temperature": temperature}
    if response_format:
        kwargs["response_format"] = response_format
    response = await llm_client.chat.completions.create(**kwargs)
    return response.choices[0].message.content
