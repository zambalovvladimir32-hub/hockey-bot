FROM mcr.microsoft.com/playwright/python:v1.50.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ПРИНУДИТЕЛЬНО качаем браузер, чтобы он точно лежал на своем месте
RUN playwright install chromium

COPY . .

CMD ["python", "bot.py"]
