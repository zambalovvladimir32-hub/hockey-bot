# Берем официальный образ со всеми установленными библиотеками
FROM mcr.microsoft.com/playwright/python:v1.50.0-jammy

WORKDIR /app

# Ставим нужные библиотеки
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Принудительно ставим сам браузер внутри сервера
RUN playwright install chromium

COPY . .

# Команда для запуска нашего парсера
CMD ["python", "main.py"]
