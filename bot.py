import asyncio
import aiohttp
import os
import json
import google.generativeai as genai
import redis.asyncio as redis # <-- ДОБАВЛЯЕМ ИМПОРТ

# Настройки среды
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL") # <-- ВАШ ПРОКСИ ИЗ RAILWAY
REDIS_URL = os.getenv("REDIS_URL") # <-- ПОДТЯНЕТСЯ ИЗ RAILWAY АВТОМАТИЧЕСКИ

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# Подключаемся к Redis. decode_responses=True нужен, чтобы получать обычные строки, а не байты
db = redis.from_url(REDIS_URL, decode_responses=True) if REDIS_URL else None

# Белый список лиг (оставляем как было)
WHITE_LIST = ["KHL", "NHL", "National Hockey League", "SHL", "Liiga", "DEL", "Extraliga", "Tipsport Liga"]

# ... (ваши функции get_raw_bundle и ai_digging оставляем, только добавьте proxy в session.get, как мы обсуждали ранее) ...

async def main():
    print("--- 🚀 v168.0: АЛГОРИТМ + AI-РЫТЬЁ ЗАПУЩЕНО ---", flush=True)
    
    # ... (отправка стартового сообщения) ...

    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        while True:
            try:
                # <-- ТУТ ИСПОЛЬЗУЕМ ПРОКСИ
                async with session.get("https://api.sofascore.com/api/v1/sport/ice-hockey/events/live", proxy=PROXY_URL, timeout=10) as r:
                    if r.status != 200: continue
                    events = (await r.json()).get('events', [])

                for ev in events:
                    mid = str(ev.get('id')) # Делаем ID строкой для удобства работы с БД
                    
                    # <-- ПРОВЕРЯЕМ В REDIS, БЫЛ ЛИ УЖЕ СИГНАЛ
                    if db:
                        is_sent = await db.sismember("sent_signals", mid)
                        if is_sent: continue
                    
                    # ... (здесь ваш алгоритм: статус 31, фильтр лиг, счет, броски, штрафы и ai_digging) ...

                    if "ПОДТВЕРЖДАЮ" in ai_report.upper():
                        # ... (здесь ваш код формирования msg) ...
                        await send_tg(msg)
                        
                        # <-- ЗАПИСЫВАЕМ ОТПРАВЛЕННЫЙ МАТЧ В REDIS
                        if db:
                            await db.sadd("sent_signals", mid)
                            # Опционально: можно хранить записи 24 часа, чтобы база не разрасталась годами
                            await db.expire("sent_signals", 86400) 

            except Exception as e: 
                print(f"Ошибка в главном цикле: {e}")
            await asyncio.sleep(20)
