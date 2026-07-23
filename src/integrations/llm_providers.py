import os
import time
import requests
from groq import Groq
from google import genai


def call_ollama(prompt: str, model: str = "llama3.2:3b", host: str = "http://127.0.0.1:11434") -> dict:
    start = time.monotonic()
    resp = requests.post(
        f"{host}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
    )
    resp.raise_for_status()
    elapsed = time.monotonic() - start
    data = resp.json()

    return {
        "provider": "ollama",
        "model": model,
        "response_text": data["response"],
        "prompt_tokens": data["prompt_eval_count"],
        "completion_tokens": data["eval_count"],
        "latency_seconds": elapsed,
        "cost_usd": 0.0,
    }


def call_groq(prompt: str, model: str = "llama-3.3-70b-versatile") -> dict:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    start = time.monotonic()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    elapsed = time.monotonic() - start

    return {
        "provider": "groq",
        "model": model,
        "response_text": resp.choices[0].message.content,
        "prompt_tokens": resp.usage.prompt_tokens,
        "completion_tokens": resp.usage.completion_tokens,
        "latency_seconds": elapsed,
        "cost_usd": 0.0,
    }


def call_gemini(prompt: str, model: str = "gemini-flash-latest") -> dict:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    start = time.monotonic()
    resp = client.models.generate_content(model=model, contents=prompt)
    elapsed = time.monotonic() - start

    return {
        "provider": "gemini",
        "model": model,
        "response_text": resp.text,
        "prompt_tokens": resp.usage_metadata.prompt_token_count,
        "completion_tokens": resp.usage_metadata.candidates_token_count,
        "latency_seconds": elapsed,
        "cost_usd": 0.0,
    }


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    result = call_ollama("What is subrogation in insurance?")
    print(result)

    result = call_groq("What is subrogation in insurance?")
    print(result)

    result = call_gemini("What is subrogation in insurance?")
    print(result)
