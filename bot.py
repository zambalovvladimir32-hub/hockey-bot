import asyncio
import aiohttp
import os
import logging
import google.generativeai as genai
from aiogram import Bot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Настройка бесплатного ИИ Google
genai.configure(api_key=GEMINI_KEY)
# Используем самую быструю и доступную модель
ai_model = genai.GenerativeModel('gemini-1.5-flash')

bot = Bot(token=TOKEN)

URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/8"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}

sent_matches = set()

async def get_ai_prediction(match_data):
    try:
        # Ускоренный запрос к Gemini
        prompt = f"Короткий хоккейный прогноз на матч {match_data}. Максимум 7 слов."
        response = await asyncio.to_thread(ai_model.generate_content, prompt)
        return f"🤖 {response.text.strip()}"
    except Exception as e:
        logger.error(f"ИИ временно недоступен: {e}")
        return "🤖 Анализ: Ожидается высокая активность в зоне атаки."

async def check_all_leagues():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(URL, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    stages = data.get('Stages', [])
                    
                    for stage in stages:
                        league_name = stage.get('Snm', 'Хоккей')
                        events = stage.get('Events', [])
                        
                        for event in events:
                            eid = event.get('Eid')
                            if eid in sent_matches: continue
                            
                            # Собираем данные матча
                            t1 = event.get('T1', [{}])[0].get('Nm', 'Команда 1')
                            t2 = event.get('T2', [{}])[0].get('Nm', 'Команда 2')
                            s1 = event.get('Tr1', '0')
                            s2 = event.get('Tr2', '0')
                            status = event.get('Eps', 'LIVE')

                            # Сначала генерируем прогноз
                            prediction = await get_ai_prediction(f"{t1} vs {t2}")

                            msg = (f"🏒 **{league_name}**\n"
                                   f"⚔️ **{t1} — {t2}**\n"
                                   f"📊 Счет: `{s1}:{s2}` ({status})\n"
                                   f"{prediction}")

                            await bot.send_message(CHANNEL_ID, msg)
                            sent_matches.add(eid)
                            # Короткая пауза для стабильности Telegram
                            await asyncio.sleep(1)
                else:
                    logger.error(f"Livescore API вернул: {resp.status}")
        except Exception as e:
            logger.error(f"Ошибка сети: {e}")

async def main():
    # Сообщение о запуске, чтобы ты видел результат сразу
    try:
        await bot.send_message(CHANNEL_ID, "✅ **Система мониторинга КХЛ/МХЛ/ВХЛ запущена!**\nИщу все доступные матчи...")
    except: pass
    
    while True:
        await check_all_leagues()
        # Проверяем каждые 45 секунд — это золотая середина
        await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(main())
