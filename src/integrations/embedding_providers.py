import os

import requests
from google import genai
from google.genai import types


def embed_ollama(text: str, model: str = "nomic-embed-text", host: str = "http://127.0.0.1:11434") -> list[float]:
    resp = requests.post(f"{host}/api/embed", json={"model": model, "input": text})
    resp.raise_for_status()
    return resp.json()["embeddings"][0]


def embed_gemini(text: str, model: str = "gemini-embedding-001", output_dimensionality: int | None = None) -> list[float]:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    config = types.EmbedContentConfig(output_dimensionality=output_dimensionality) if output_dimensionality else None
    resp = client.models.embed_content(model=model, contents=text, config=config)
    return resp.embeddings[0].values


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    for name, fn in [("ollama", embed_ollama), ("gemini", embed_gemini)]:
        vec = fn("What is the wind/hail deductible?")
        print(f"{name}: {len(vec)} dimensions, first 3 = {vec[:3]}")
