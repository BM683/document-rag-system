import os
import httpx

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

def groq_chat_completion(messages, model="llama3-8b-8192", temperature=0.2, max_tokens=512):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(GROQ_ENDPOINT, headers=headers, json=data)
        resp.raise_for_status()
        return resp.json()
