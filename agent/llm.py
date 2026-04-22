from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI

from config import GOOGLE_API_KEY, MODEL_NAME


@lru_cache(maxsize=2)
def get_llm(temperature: float = 0.2) -> ChatGoogleGenerativeAI:
    if not GOOGLE_API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Put it in a .env file or export it "
            "before running the app."
        )
    return ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        google_api_key=GOOGLE_API_KEY,
        temperature=temperature,
    )
