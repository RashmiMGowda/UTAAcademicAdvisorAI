import os

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = lambda *args, **kwargs: None

try:
    from openai import OpenAI, AsyncOpenAI
except Exception:
    OpenAI = None
    AsyncOpenAI = None


def load_env() -> None:
    load_dotenv(override=False)


def get_openai_api_key(explicit_key: str | None = None) -> str:
    load_env()
    api_key = (explicit_key or os.getenv("OPENAI_API_KEY", "")).strip()
    if not api_key or "YOUR_" in api_key or api_key.endswith("HERE"):
        raise RuntimeError(
            "OpenAI API key is missing. Add your real key in the project .env file as "
            "OPENAI_API_KEY=sk-... or paste it into the Streamlit sidebar."
        )
    return api_key


def get_openai_base_url() -> str:
    load_env()
    return os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()


def create_openai_client(explicit_key: str | None = None) -> OpenAI:
    if OpenAI is None:
        raise RuntimeError("openai package not installed. Run `pip install -r requirements.txt`.")
    return OpenAI(api_key=get_openai_api_key(explicit_key), base_url=get_openai_base_url())


def create_async_openai_client(explicit_key: str | None = None) -> AsyncOpenAI:
    if AsyncOpenAI is None:
        raise RuntimeError("openai package not installed. Run `pip install -r requirements.txt`.")
    return AsyncOpenAI(
        api_key=get_openai_api_key(explicit_key),
        base_url=get_openai_base_url(),
    )
