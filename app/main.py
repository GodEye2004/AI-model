from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import requests
import re
import json
from difflib import SequenceMatcher
from typing import Optional
import os

app = FastAPI()

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set OLLAMA URL from environment variable or use default
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://0.0.0.0:11434")
OLLAMA_API = f"{OLLAMA_URL}/api/chat"

TXT_PATH = "dataset.txt"
CACHE_FILE = "cache.json"

def load_text_from_txt(txt_path):
    if os.path.exists(txt_path):
        with open(txt_path, "r", encoding="utf-8") as file:
            return file.read().strip()
    return "فایل مورد نظر یافت نشد."

pdf_text = load_text_from_txt(TXT_PATH)

def clean_and_shorten_text(text):
    text = re.sub(r'\b[a-zA-Z0-9]+\b', '', text)
    return text.split('.')[0] + "." if '.' in text else text

# Load cache from file
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return {}
    return {}

# Save cache to file
def save_cache():
    with open(CACHE_FILE, "w", encoding="utf-8") as file:
        json.dump(cache, file, ensure_ascii=False, indent=4)

cache = load_cache()

def find_similar_question(new_question):
    for cached_question in cache.keys():
        if SequenceMatcher(None, cached_question, new_question).ratio() > 0.85:
            return cache[cached_question]
    return None

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat(request: ChatRequest):
    user_message = request.message.strip()

    if not user_message:
        raise HTTPException(status_code=400, detail="لطفاً یک سوال وارد کنید.")

    cached_result = find_similar_question(user_message)
    if cached_result:
        return {"response": cached_result}

    prompt = (
        f"متن:\n{pdf_text}\n\n"
        f"سؤال: {user_message}\n\n"
        f"لطفاً به زبان فارسی پاسخ بده:\n"
        f"پاسخ را فقط به زبان فارسی بده و از هیچ کلمه انگلیسی استفاده نکن."
        f"اگر سوال به متن بالا مرتبط نبود، بگو 'اطلاعاتی ندارم'.\n"
        f"اگر از کلاهبرداری بودن پرسید، بگو 'خیر، شرکت هومینگر به شما این تضمین را می‌دهد که این کار کلاهبرداری نیست'.\n"
        f"اگر پرسید این کار سودآور است یا نه، بگو 'بله، این کار سودآور است'.\n"
        f"لطفاً جواب را به صورت مختصر و واضح بده."
    )

    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            OLLAMA_API,
            json={"model": "partai/dorna-llama3", "messages": [{"role": "user", "content": prompt}], "stream": False},
            headers=headers,
        )
        response.encoding = 'utf-8'
        response_data = response.json()
        assistant_message = response_data.get("message", {}).get("content", "متوجه نشدم!")
    except Exception:
        raise HTTPException(status_code=500, detail="خطایی رخ داده است، لطفاً دوباره تلاش کنید.")

    assistant_message = clean_and_shorten_text(assistant_message)
    if "اطلاعاتی ندارم" in assistant_message or len(assistant_message) < 10:
        return {"response": "اطلاعاتی ندارم."}

    cache[user_message] = assistant_message
    save_cache()  # Save cache to file

    return {"response": assistant_message}

class SubscribeRequest(BaseModel):
    email: str

@app.post("/subscribe")
async def subscribe(request: SubscribeRequest):
    if request.email:
        return {"response": "اشتراک شما با موفقیت ثبت شد!"}
    raise HTTPException(status_code=400, detail="لطفاً ایمیل معتبر وارد کنید.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
