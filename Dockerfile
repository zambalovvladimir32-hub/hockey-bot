# Берем официальный образ со всеми установленными библиотеками для браузера
FROM mcr.microsoft.com/playwright/python:v1.50.0-jammy

WORKDIR /app

# Копируем список библиотек и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все остальные файлы бота
COPY . .

# Команда для запуска нашего тестового файла
CMD CMD ["python", "bot.py"]
