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

# НОВАЯ ТОЧКА ВХОДА - Резервный поток данных
URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/0"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Mobile Safari/537.36",
    "X-Requested-With": "com.livescore.app",
    "Accept": "*/*"
}

sent_signals = set()

async def get_ai_prediction(match_data, algo):
    try:
        res = client.models.generate_content(model="gemini-1.5-flash", contents=f"Анализ хоккея: {match_data}, {algo}. Дай короткий прогноз.")
        return f"🤖 AI: {res.text.strip()}"
    except:
        return "🤖 AI: Ожидаем активность в атаке."

async def check_logic():
    logger.info("--- ФОРСИРОВАННОЕ СКАНИРОВАНИЕ ---")
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            # Добавляем рандомный параметр к URL, чтобы обмануть кэш сервера
            ts = int(asyncio.get_event_loop().time())
            async with session.get(f"{URL}?MD=1&ts={ts}", timeout=15) as resp:
                if resp.status != 200:
                    logger.error(f"Сервер отклонил запрос: {resp.status}")
                    return
                
                data = await resp.json()
                total = 0
                
                for stage in data.get('Stages', []):
                    league = stage.get('Snm', 'Hockey')
                    for event in stage.get('Events', []):
                        total += 1
                        eid = event.get('Eid')
                        t1, t2 = event['T1'][0]['Nm'], event['T2'][0]['Nm']
                        period = event.get('Eps')
                        
                        try:
                            # Пробуем достать время из разных полей (Emm или Esh)
                            m = int(event.get('Emm') or event.get('Esh', 0))
                            s1 = int(event.get('Tr1', 0))
                            s2 = int(event.get('Tr2', 0))
                        except: continue

                        logger.info(f"НАШЕЛ: {t1}-{t2} | {m} мин | {s1}:{s2} ({league})")

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
                
                logger.info(f"ИТОГ: Обработано {total} матчей.")
        except Exception as e:
            logger.error(f"Критический сбой: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🔄 Попытка №5: Смена протокола данных. Ищу ВХЛ...")
    while True:
        await check_logic()
        await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())
