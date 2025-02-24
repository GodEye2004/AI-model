from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import requests
import re
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
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_API = f"{OLLAMA_URL}/api/chat"

TXT_PATH = "dataset.txt"

def load_text_from_txt(txt_path):
    try:
        with open(txt_path, "r", encoding="utf-8") as file:
            return file.read().strip()
    except FileNotFoundError:
        return "فایل مورد نظر یافت نشد."

pdf_text = load_text_from_txt(TXT_PATH)

def clean_and_shorten_text(text):
    text = re.sub(r'\b[a-zA-Z0-9]+\b', '', text)
    return text.split('.')[0] + "." if '.' in text else text

cache = {}

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
        f"پاسخ را فقط به زبان فارسی بده و از هیچ کلمه انگلیسی استفاده نکن.\n"
        f"اگر سوال به متن بالا مرتبط نبود، بگو 'اطلاعاتی ندارم'.\n"
        f"اگر از کلاهبرداری بودن پرسید، بگو 'خیر، شرکت هومینگر به شما این تضمین را می‌دهد که این کار کلاهبرداری نیست'.\n"
        f"اگر پرسید این کار سودآور است یا نه، بگو 'بله، این کار سودآور است'.\n"
        f"لطفاً جواب را به صورت مختصر و واضح بده."
    )

    try:
        headers = {
            "Content-Type": "application/json",
            "Accept-Charset": "utf-8"
        }
        response = requests.post(
            OLLAMA_API,
            json={
                "model": "partai/dorna-llama3",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            },
            headers=headers
        )
        response.encoding = 'utf-8'  # Force UTF-8 encoding
        response_data = response.json()
        assistant_message = response_data.get("message", {}).get("content", "متوجه نشدم!")
    except Exception as e:
        print(f"خطای ارتباط با API Ollama: {e}")
        raise HTTPException(status_code=500, detail="خطایی رخ داده است، لطفاً دوباره تلاش کنید.")

    assistant_message = clean_and_shorten_text(assistant_message)

    if "اطلاعاتی ندارم" in assistant_message or len(assistant_message) < 10:
        return {"response": "اطلاعاتی ندارم."}

    cache[user_message] = assistant_message

    return {"response": assistant_message}

class SubscribeRequest(BaseModel):
    email: str

@app.post("/subscribe")
async def subscribe(request: SubscribeRequest):
    if request.email:
        return {"response": "اشتراک شما با موفقیت ثبت شد!"}
    raise HTTPException(status_code=400, detail="لطفاً ایمیل معتبر وارد کنید.")

