# groq_client.py
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

def groq_chat_completion(messages, model="llama-3.1-8b-instant", temperature=0.7, max_tokens=1000):
    """Call Groq API for chat completion with detailed error logging"""
    
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment")
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    # DEBUG: Print what we're sending
    print(f"🔍 Sending to Groq:")
    print(f"URL: {url}")
    print(f"Model: {model}")
    print(f"Messages count: {len(messages)}")
    print(f"Max tokens: {max_tokens}")
    
    # Check message lengths
    for i, msg in enumerate(messages):
        print(f"Message {i} ({msg['role']}): {len(msg['content'])} chars")
    
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            
            if resp.status_code != 200:
                print(f"❌ Groq API Error: {resp.status_code}")
                print(f"Response: {resp.text}")
                print(f"Request payload: {payload}")
            
            resp.raise_for_status()
            return resp.json()
            
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP Error: {e}")
        print(f"Response content: {e.response.text if e.response else 'No response'}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise
