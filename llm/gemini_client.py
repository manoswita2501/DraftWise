import os
from dotenv import load_dotenv
from google import genai

MODEL_DEFAULT = "gemini-2.5-flash-lite" 

def get_client():
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GOOGLE_API_KEY. Put it in a .env file in the project root.")
    return genai.Client(api_key=api_key)

def generate_text(prompt: str, model: str = MODEL_DEFAULT) -> str:
    client = get_client()
    resp = client.models.generate_content(model=model, contents=prompt)
    return (resp.text or "").strip()