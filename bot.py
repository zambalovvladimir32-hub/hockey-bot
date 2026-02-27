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

# ПРЯМОЙ URL К ДАННЫМ (БЕЗ ПОСРЕДНИКОВ)
URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/0?MD=1"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://www.livescore.com",
    "Referer": "https://www.livescore.com/"
}

sent_signals = set()

async def get_ai_prediction(match_data, algo):
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=f"Ты эксперт по хоккею. Матч: {match_data}. Стратегия: {algo}. Дай прогноз до 6 слов."
        )
        return f"🤖 AI: {response.text.strip()}"
    except:
        return "🤖 AI: Ожидается высокая интенсивность игры."

async def check_logic():
    logger.info("--- ПОИСК МАТЧЕЙ (МЕТОД 3) ---")
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(URL, timeout=15) as resp:
                if resp.status != 200:
                    logger.error(f"Доступ ограничен (Status {resp.status}).")
                    return
                
                data = await resp.json()
                total = 0
                
                for stage in data.get('Stages', []):
                    league = stage.get('Snm', 'League')
                    for event in stage.get('Events', []):
                        total += 1
                        eid = event.get('Eid')
                        t1, t2 = event['T1'][0]['Nm'], event['T2'][0]['Nm']
                        period = event.get('Eps')
                        
                        # Если нет минут, пробуем достать из другого поля
                        min_raw = event.get('Emm') or event.get('Esh', 0)
                        try:
                            m = int(min_raw)
                            s1 = int(event.get('Tr1', 0))
                            s2 = int(event.get('Tr2', 0))
                        except: continue

                        # Вывод в логи для контроля
                        if period in ['1ST', '2ND']:
                            logger.info(f"В ЭФИРЕ: {t1}-{t2} | {m} мин | {s1}:{s2}")

                        algo = None
                        if period == '1ST' and 11 <= m <= 19 and (s1 + s2 <= 1):
                            algo = "💎 ЗАСУХА (1-й ПЕР)"
                        elif period == '2ND' and 21 <= m <= 35:
                            algo = "🔥 ТОТАЛ (2-й ПЕР)"

                        if algo:
                            key = f"{eid}_{algo}"
                            if key not in sent_signals:
                                ai_text = await get_ai_prediction(f"{t1}-{t2}", algo)
                                msg = f"🚨 **{algo}**\n🏒 {t1} — {t2}\n📊 Счет: `{s1}:{s2}` ({m} мин)\n🏆 {league}\n\n{ai_text}"
                                await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                sent_signals.add(key)
                                logger.info(f"ОТПРАВЛЕНО: {t1}-{t2}")

                logger.info(f"УСПЕШНО: Найдено {total} матчей.")
        except Exception as e:
            logger.error(f"Ошибка: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🚀 Бот перезагружен. Ищу матчи ВХЛ...")
    while True:
        await check_logic()
        await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())
