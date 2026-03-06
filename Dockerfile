# Берем легкую базу
FROM python:3.11-slim

WORKDIR /app

# Сначала копируем только список зависимостей
COPY requirements.txt .

# Устанавливаем и curl_cffi, и playwright из списка
RUN pip install --no-cache-dir -r requirements.txt

# Скачиваем сам браузер Chromium для Playwright
RUN playwright install chromium
RUN playwright install-deps

# Копируем остальной код бота
COPY . .

# Запускаем!
CMD ["python", "bot.py"]
