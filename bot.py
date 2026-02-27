import asyncio
import aiohttp
import os
import logging
import sys
from google import genai
from aiogram import Bot

# Настройка логов для Amvera
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

# Данные из Amvera
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

bot = Bot(token=TOKEN)
client = genai.Client(api_key=GEMINI_KEY)

URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/0.00"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

sent_signals = set()

async def get_ai_prediction(match_data, algo):
    """Запрос аналитики у Gemini"""
    try:
        prompt = f"Ты эксперт по хоккею. Стратегия: {algo}. Матч: {match_data}. Дай прогноз на остаток периода в 5-7 словах."
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        return f"🤖 AI: {response.text.strip()}"
    except Exception as e:
        logger.error(f"Ошибка Gemini: {e}")
        return "🤖 AI: Ожидается высокая активность в атаке."

async def check_logic():
    logger.info("--- СКАНИРОВАНИЕ ЛИНИИ ---")
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(URL, timeout=15) as resp:
                data = await resp.json()
                
                for stage in data.get('Stages', []):
                    for event in stage.get('Events', []):
                        eid = event.get('Eid')
                        t1, t2 = event['T1'][0]['Nm'], event['T2'][0]['Nm']
                        period = event.get('Eps')
                        
                        try:
                            m = int(event.get('Emm', 0))
                            s1, s2 = int(event.get('Tr1', 0)), int(event.get('Tr2', 0))
                        except: continue

                        found_algo = None
                        # 1. Засуха в 1-м периоде
                        if period == '1ST' and 12 <= m <= 18 and (s1 + s2 <= 1):
                            found_algo = "💎 ЗАСУХА (1-й ПЕР)"
                        # 2. Активность во 2-м периоде
                        elif period == '2ND' and 21 <= m <= 32:
                            found_algo = "🔥 ТОТАЛ (2-й ПЕР)"
                        # 3. Погоня (Камбэк)
                        elif period == '2ND' and abs(s1 - s2) >= 2 and (s1 + s2 < 6):
                            found_algo = "🧨 ОЖИДАЕМ КАМБЭК"

                        if found_algo:
                            key = f"{eid}_{found_algo}"
                            if key not in sent_signals:
                                logger.info(f"СИГНАЛ: {t1}-{t2}")
                                ai_text = await get_ai_prediction(f"{t1}-{t2} (Счет {s1}:{s2})", found_algo)
                                
                                msg = (
                                    f"🚨 **{found_algo}**\n"
                                    f"🏒 **{t1} — {t2}**\n"
                                    f"📊 Счет: `{s1}:{s2}` ({m} мин)\n\n"
                                    f"{ai_text}"
                                )
                                
                                await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                sent_signals.add(key)

        except Exception as e:
            logger.error(f"Ошибка в цикле: {e}")

async def main():
    logger.info("БОЕВОЙ РЕЖИМ ЗАПУЩЕН")
    while True:
        await check_logic()
        await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(main())
