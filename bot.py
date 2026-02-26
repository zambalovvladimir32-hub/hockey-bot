import asyncio
import aiohttp
import os
import logging
from google import genai  # Новая библиотека, которую просит лог
from aiogram import Bot

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Данные из Amvera
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Новый клиент для работы с ИИ
client = genai.Client(api_key=GEMINI_KEY)
bot = Bot(token=TOKEN)

URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/8"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}

sent_signals = set()

async def get_ai_prediction(match_data, algo_name):
    try:
        # Новый формат вызова Gemini 1.5
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=f"Ты эксперт-каппер. Стратегия: {algo_name}. Матч: {match_data}. Дай совет по ставке в 5 словах."
        )
        return f"🤖 {response.text.strip()}"
    except Exception as e:
        logger.error(f"Ошибка ИИ: {e}")
        return "🤖 Анализ: Высокая вероятность реализации голевого момента."

async def check_logic():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(URL, timeout=15) as resp:
                if resp.status != 200: return
                data = await resp.json()
                
                for stage in data.get('Stages', []):
                    for event in stage.get('Events', []):
                        eid = event.get('Eid')
                        period = event.get('Eps') 
                        try: minute = int(event.get('Emm', 0))
                        except: minute = 0
                        s1, s2 = int(event.get('Tr1', 0)), int(event.get('Tr2', 0))

                        found_algo = None
                        
                        # 1. Засуха (12-17 мин, счет 0:0, 1:0, 0:1)
                        if period == '1ST' and 12 <= minute <= 17:
                            if (s1 == 0 and s2 == 0) or (s1 == 1 and s2 == 0) or (s1 == 0 and s2 == 1):
                                found_algo = "ЗАСУХА 1-Й ПЕР (ТБ 0.5/1.5)"

                        # 2. Гол во 2-м (21-30 мин)
                        elif period == '2ND' and 21 <= minute <= 30:
                            found_algo = "ГОЛ ВО 2-М ПЕРИОДЕ (ТБ 0.5)"

                        # 3. Камбэк (2-й период, разрыв 1-2 шайбы)
                        elif period == '2ND' and (abs(s1 - s2) in [1, 2]) and (s1 + s2 < 5):
                            found_algo = "ОЖИДАЕМ КАМБЭК (ИТБ)"

                        if found_algo:
                            key = f"{eid}_{found_algo}"
                            if key not in sent_signals:
                                t1 = event['T1'][0]['Nm']
                                t2 = event['T2'][0]['Nm']
                                comment = await get_ai_prediction(f"{t1}-{t2}, счет {s1}:{s2}", found_algo)
                                
                                msg = (f"🚨 **СИГНАЛ: {found_algo}**\n"
                                       f"⚔️ **{t1} — {t2}**\n"
                                       f"📊 Счет: `{s1}:{s2}`\n"
                                       f"⏱ Время: `{minute}' мин`\n\n"
                                       f"{comment}")

                                await bot.send_message(CHANNEL_ID, msg)
                                sent_signals.add(key)
                                logger.info(f"Успех! Сигнал отправлен: {t1}-{t2}")

        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}")

async def main():
    while True:
        await check_logic()
        await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())
