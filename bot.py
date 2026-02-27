import asyncio
import aiohttp
import os
import logging
import sys
import random
from google import genai
from aiogram import Bot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

bot = Bot(token=TOKEN)
client = genai.Client(api_key=GEMINI_KEY)

# НОВЫЙ ИСТОЧНИК (Flashscore-like API поток)
URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/0"

sent_signals = set()

async def get_ai_prediction(match_data, algo):
    try:
        res = client.models.generate_content(model="gemini-1.5-flash", contents=f"Хоккей: {match_data}, {algo}. Дай короткий прогноз до 6 слов.")
        return f"🤖 AI: {res.text.strip()}"
    except:
        return "🤖 AI: Высокая вероятность гола в ближайшее время."

async def check_logic():
    # Имитируем современный браузер Chrome на Windows
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.livescore.com",
        "Referer": "https://www.livescore.com/",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    logger.info("--- ПОПЫТКА ОБХОДА БЛОКИРОВКИ (FLASH-METHOD) ---")
    
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            # Добавляем случайное число к запросу, чтобы не получать пустой кэш
            random_tail = random.randint(1000, 9999)
            async with session.get(f"{URL}?MD=1&random={random_tail}", timeout=20) as resp:
                if resp.status != 200:
                    logger.error(f"Сервер отклонил запрос (Код {resp.status})")
                    return
                
                data = await resp.json()
                total = 0
                
                for stage in data.get('Stages', []):
                    league = stage.get('Snm', 'Hockey')
                    for event in stage.get('Events', []):
                        total += 1
                        t1, t2 = event['T1'][0]['Nm'], event['T2'][0]['Nm']
                        period = event.get('Eps')
                        
                        try:
                            # Парсим минуты и счет
                            m = int(event.get('Emm') or event.get('Esh', 0))
                            s1 = int(event.get('Tr1', 0))
                            s2 = int(event.get('Tr2', 0))
                        except: continue

                        logger.info(f"ВИЖУ: {t1}-{t2} | {period} {m} мин | {s1}:{s2}")

                        # Алгоритмы
                        algo = None
                        if period == '1ST' and 11 <= m <= 19 and (s1 + s2 <= 1):
                            algo = "💎 ЗАСУХА (1-й ПЕР)"
                        elif period == '2ND' and 21 <= m <= 35:
                            algo = "🔥 ТОТАЛ (2-й ПЕР)"

                        if algo:
                            key = f"{event['Eid']}_{algo}"
                            if key not in sent_signals:
                                ai_text = await get_ai_prediction(f"{t1}-{t2}", algo)
                                msg = f"🚨 **{algo}**\n🏒 {t1} — {t2}\n📊 Счет: `{s1}:{s2}` ({m} мин)\n🏆 {league}\n\n{ai_text}"
                                await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                sent_signals.add(key)
                                logger.info(f"СИГНАЛ ОТПРАВЛЕН: {t1}-{t2}")

                logger.info(f"УСПЕШНО: В лайве найдено {total} матчей.")
        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🔄 Бот обновлен. Пытаюсь «пробить» ВХЛ через Flash-протокол...")
    while True:
        await check_logic()
        # Немного увеличим интервал, чтобы не злить сервер
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
