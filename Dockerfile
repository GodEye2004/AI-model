# از ایمیج رسمی پایتون استفاده می‌کنیم
FROM python:3.10-slim

# تنظیم دایرکتوری کاری
WORKDIR /app

# کپی فایل‌های پروژه به داکر
COPY . .

# نصب پکیج‌های مورد نیاز
RUN pip install --no-cache-dir -r requirements.txt

# باز کردن پورت 8080
EXPOSE 8080

# اجرای اپلیکیشن
CMD ["python", "app.py"]
