from flask import Flask, request, jsonify
from flask_caching import Cache
from flask_cors import CORS
import requests
import re
from difflib import SequenceMatcher

app = Flask(__name__)
CORS(app)  
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

TXT_PATH = "dataset.txt"

# بارگذاری متن از فایل متنی
def load_text_from_txt(txt_path):
    try:
        with open(txt_path, "r", encoding="utf-8") as file:
            return file.read().strip()
    except FileNotFoundError:
        return "فایل مورد نظر یافت نشد."

pdf_text = load_text_from_txt(TXT_PATH)

# حذف کلمات انگلیسی و کوتاه کردن پاسخ
def clean_and_shorten_text(text):
    text = re.sub(r'\b[a-zA-Z0-9]+\b', '', text) 
    return text.split('.')[0] + "." if '.' in text else text

# بررسی شباهت سوال جدید با سوالات کش‌شده
def find_similar_question(new_question):
    for cached_question in cache.cache._cache:
        if SequenceMatcher(None, cached_question, new_question).ratio() > 0.85:
            return cache.get(cached_question)
    return None

# کلید API DeepInfra
API_KEY = "dXNHpu40f03udvFd87VaJ7QMuZzHuine"  # API Key که از DeepInfra گرفتی
MODEL_ID = "deepseek-ai/DeepSeek-R1"  # مدل جدید DeepSeek-R1

# ارسال درخواست به DeepInfra API
def get_response_from_deepinfra(prompt):
    url = f"https://api.deepinfra.com/v1/models/{MODEL_ID}/predict"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 200  # تعداد توکن‌هایی که در پاسخ می‌خواهی
        }
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()['generated_text']
        else:
            return "خطای ارتباط با مدل."
    except Exception as e:
        print(f"خطا در ارتباط با API: {e}")
        return "خطای رخ داده است. لطفاً دوباره تلاش کنید."

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"response": "لطفاً یک سوال وارد کنید."})

    cached_result = find_similar_question(user_message)
    if cached_result:
        return jsonify({"response": cached_result})

    prompt = (
        f"متن:\n{pdf_text}\n\n"
        f"سؤال: {user_message}\n\n"
        f"پاسخ را فقط به زبان فارسی بده و از هیچ کلمه انگلیسی استفاده نکن.\n"
        f"اگر سوال به متن بالا مرتبط نبود، بگو 'اطلاعاتی ندارم'.\n"
        f"لطفاً جواب را به صورت مختصر و واضح بده."
    )

    assistant_message = get_response_from_deepinfra(prompt)

    assistant_message = clean_and_shorten_text(assistant_message)

    if "اطلاعاتی ندارم" in assistant_message or len(assistant_message) < 10:
        return jsonify({"response": "اطلاعاتی ندارم."})

    # ذخیره کردن نتیجه در کش
    cache.set(user_message, assistant_message, timeout=300)

    return jsonify({"response": assistant_message})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
