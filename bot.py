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

# НОВЫЙ ГЛОБАЛЬНЫЙ URL (Видит ВХЛ и КХЛ)
URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/0"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

sent_signals = set()

async def get_ai_prediction(match_data, algo):
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=f"Ты эксперт по хоккею. Матч: {match_data}. Стратегия: {algo}. Дай прогноз на остаток периода до 6 слов."
        )
        return f"🤖 AI: {response.text.strip()}"
    except:
        return "🤖 AI: Ожидается результативная игра."

async def check_logic():
    logger.info("--- ГЛОБАЛЬНОЕ СКАНИРОВАНИЕ ---")
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(URL, timeout=15) as resp:
                data = await resp.json()
                total = 0
                for stage in data.get('Stages', []):
                    league = stage.get('Snm', '')
                    for event in stage.get('Events', []):
                        total += 1
                        eid = event.get('Eid')
                        t1, t2 = event['T1'][0]['Nm'], event['T2'][0]['Nm']
                        period = event.get('Eps')
                        try:
                            m = int(event.get('Emm', 0))
                            s1, s2 = int(event.get('Tr1', 0)), int(event.get('Tr2', 0))
                        except: continue

                        # Пишем в логи ВСЁ, что видим в 1-м и 2-м периодах
                        if period in ['1ST', '2ND']:
                            logger.info(f"ВИЖУ: {t1}-{t2} | {m} мин | {s1}:{s2} ({league})")

                        algo = None
                        if period == '1ST' and 11 <= m <= 19 and (s1 + s2 <= 1):
                            algo = "💎 ЗАСУХА (1-й ПЕР)"
                        elif period == '2ND' and 21 <= m <= 35:
                            algo = "🔥 ТОТАЛ (2-й ПЕР)"

                        if algo:
                            key = f"{eid}_{algo}"
                            if key not in sent_signals:
                                logger.info(f"!!! СИГНАЛ: {t1}-{t2} !!!")
                                ai_text = await get_ai_prediction(f"{t1}-{t2}", algo)
                                msg = f"🚨 **{algo}**\n🏒 {t1} — {t2}\n📊 Счет: `{s1}:{s2}` ({m} мин)\n🏆 {league}\n\n{ai_text}"
                                await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                sent_signals.add(key)
                
                logger.info(f"ВСЕГО МАТЧЕЙ В ОБРАБОТКЕ: {total}")
        except Exception as e:
            logger.error(f"Ошибка: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "✅ Бот прозрел! Начинаю поиск ВХЛ и других лиг.")
    while True:
        await check_logic()
        await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(main())
