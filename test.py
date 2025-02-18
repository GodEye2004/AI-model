from flask import Flask, request, jsonify
from flask_caching import Cache
from flask_cors import CORS
import ollama
import re
from difflib import SequenceMatcher

app = Flask(__name__)
CORS(app)  
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

TXT_PATH = "dataset.txt"

def load_text_from_txt(txt_path):
    """ بارگذاری متن از فایل متنی """
    try:
        with open(txt_path, "r", encoding="utf-8") as file:
            return file.read().strip()
    except FileNotFoundError:
        return "فایل مورد نظر یافت نشد."

pdf_text = load_text_from_txt(TXT_PATH)

def clean_and_shorten_text(text):
    """ حذف کلمات انگلیسی و کوتاه کردن پاسخ """
    text = re.sub(r'\b[a-zA-Z0-9]+\b', '', text) 
    return text.split('.')[0] + "." if '.' in text else text

def find_similar_question(new_question):
    """ بررسی شباهت سوال جدید با سوالات کش‌شده """
    for cached_question in cache.cache._cache:
        if SequenceMatcher(None, cached_question, new_question).ratio() > 0.85:
            return cache.get(cached_question)
    return None

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
    f"اگر از کلاهبرداری بودن پرسید، بگو 'خیر، شرکت هومینگر به شما این تضمین را می‌دهد که این کار کلاهبرداری نیست'.\n"
    f"اگر پرسید این کار سودآور است یا نه، بگو 'بله، این کار سودآور است'.\n"
    f"لطفاً جواب را به صورت مختصر و واضح بده."
    )

    try:
        response = ollama.chat(model="partai/dorna-llama3", messages=[{"role": "user", "content": prompt}])
        assistant_message = response.get("message", {}).get("content", "متوجه نشدم!")
    except Exception as e:
        print(f"خطای ارتباط با مدل: {e}")
        return jsonify({"response": "خطایی رخ داده است، لطفاً دوباره تلاش کنید."})

    assistant_message = clean_and_shorten_text(assistant_message)

    if "اطلاعاتی ندارم" in assistant_message or len(assistant_message) < 10:
        return jsonify({"response": "اطلاعاتی ندارم."})

    cache.set(user_message, assistant_message, timeout=300)

    # اینجا می‌توانیم منبع درآمدزایی اضافه کنیم (مثلاً نمایش آگهی‌ها)
    # درآمدزایی از طریق تبلیغات یا عضویت ویژه
    return jsonify({"response": assistant_message})

# نمونه‌ای از لایه مدیریت اشتراک
@app.route("/subscribe", methods=["POST"])
def subscribe():
    data = request.get_json()
    user_email = data.get("email")
    if user_email:
        # فرض کنیم اینجا یک سیستم اشتراکی داریم
        return jsonify({"response": "اشتراک شما با موفقیت ثبت شد!"})
    return jsonify({"response": "لطفاً ایمیل معتبر وارد کنید."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
