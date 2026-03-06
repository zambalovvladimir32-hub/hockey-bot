FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
# Устанавливаем и curl_cffi, и playwright
RUN pip install --no-cache-dir -r requirements.txt playwright
RUN playwright install chromium
RUN playwright install-deps
COPY . .
CMD ["python", "bot.py"]
