import asyncio
import aiohttp
import os
import logging
import sys
from google import genai
from aiogram import Bot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

bot = Bot(token=TOKEN)
client = genai.Client(api_key=GEMINI_KEY)

# НОВАЯ ТОЧКА ВХОДА (Резервный API поток)
URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/0"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15",
    "Accept": "application/json",
    "X-Requested-With": "com.livescore.app" # Прикидываемся мобильным приложением
}

sent_signals = set()

async def get_ai_prediction(match_data, algo):
    try:
        res = client.models.generate_content(model="gemini-1.5-flash", contents=f"Прогноз на хоккей: {match_data}, {algo}. 5 слов.")
        return f"🤖 AI: {res.text.strip()}"
    except:
        return "🤖 AI: Ожидается активность."

async def check_logic():
    logger.info("--- ПОПЫТКА ПРОРЫВА (МЕТОД 4) ---")
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            # Добавляем случайный параметр, чтобы сервер не выдавал старый кэш с 0 матчей
            async with session.get(f"{URL}?t={asyncio.get_event_loop().time()}", timeout=15) as resp:
                data = await resp.json()
                total = 0
                
                for stage in data.get('Stages', []):
                    for event in stage.get('Events', []):
                        total += 1
                        t1, t2 = event['T1'][0]['Nm'], event['T2'][0]['Nm']
                        period = event.get('Eps')
                        
                        # Собираем данные
                        try:
                            m = int(event.get('Emm', 0))
                            s1, s2 = int(event.get('Tr1', 0)), int(event.get('Tr2', 0))
                        except: continue

                        logger.info(f"НАШЕЛ В ЛАЙВЕ: {t1}-{t2} | {m} мин | {s1}:{s2}")

                        algo = None
                        if period == '1ST' and 11 <= m <= 19 and (s1 + s2 <= 1):
                            algo = "💎 ЗАСУХА (1-й ПЕР)"
                        elif period == '2ND' and 21 <= m <= 35:
                            algo = "🔥 ТОТАЛ (2-й ПЕР)"

                        if algo:
                            key = f"{event['Eid']}_{algo}"
                            if key not in sent_signals:
                                ai_text = await get_ai_prediction(f"{t1}-{t2}", algo)
                                msg = f"🚨 **{algo}**\n🏒 {t1} — {t2}\n📊 Счет: `{s1}:{s2}` ({m} мин)\n\n{ai_text}"
                                await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                sent_signals.add(key)
                
                logger.info(f"РЕЗУЛЬТАТ: Вижу {total} матчей.")
        except Exception as e:
            logger.error(f"ОШИБКА: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🔄 Переподключение к новому потоку данных...")
    while True:
        await check_logic()
        await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())
