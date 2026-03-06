# Берем легкую и быструю версию Python
FROM python:3.11-slim

# Создаем рабочую папку
WORKDIR /app

# Копируем список библиотек (наш curl_cffi)
COPY requirements.txt .

# Устанавливаем библиотеки
RUN pip install --no-cache-dir -r requirements.txt

# Копируем сам скрипт бота
COPY . .

# Запускаем (убедись, что твой файл называется main.py)
CMD ["python", "main.py"]
