import asyncio
import aiohttp
import os
import logging
from google import genai
from aiogram import Bot

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Новая настройка Google AI (без предупреждений)
client = genai.Client(api_key=GEMINI_KEY)
MODEL_ID = "gemini-1.5-flash"

bot = Bot(token=TOKEN)

URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/8"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

sent_signals = set()

async def get_ai_prediction(match_data, algo_name):
    try:
        prompt = f"Ты эксперт-каппер. Стратегия: {algo_name}. Матч: {match_data}. Дай совет по ставке в 5 словах."
        # Новый способ вызова Gemini
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        return f"🤖 {response.text.strip()}"
    except Exception as e:
        logger.error(f"Ошибка ИИ: {e}")
        return "🤖 Анализ: Ожидается реализация голевого момента."

async def check_logic():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(URL, timeout=10) as resp:
                if resp.status != 200: return
                data = await resp.json()
                
                for stage in data.get('Stages', []):
                    league = stage.get('Snm', 'HOCKEY')
                    for event in stage.get('Events', []):
                        eid = event.get('Eid')
                        period = event.get('Eps') 
                        try: minute = int(event.get('Emm', 0))
                        except: minute = 0
                        s1 = int(event.get('Tr1', 0))
                        s2 = int(event.get('Tr2', 0))

                        found_algo = None
                        
                        # ТВОИ АЛГОРИТМЫ
                        # 1. Засуха (12-17 мин, счета 0:0, 1:0, 0:1)
                        if period == '1ST' and 12 <= minute <= 17:
                            if (s1 == 0 and s2 == 0) or (s1 == 1 and s2 == 0) or (s1 == 0 and s2 == 1):
                                found_algo = "ЗАСУХА 1-Й ПЕР (ТБ 0.5/1.5)"

                        # 2. Гол во 2-м (21-30 мин)
                        elif period == '2ND' and 21 <= minute <= 30:
                            found_algo = "ГОЛ ВО 2-М ПЕРИОДЕ (ТБ 0.5)"

                        # 3. Камбэк (2-й период)
                        elif period == '2ND' and ((s1 == 0 and s2 >= 1) or (s2 == 0 and s1 >= 1) or abs(s1-s2) == 2):
                            if s1+s2 < 5: 
                                found_algo = "ОЖИДАЕМ КАМБЭК (ИТБ)"

                        if found_algo:
                            signal_key = f"{eid}_{found_algo}"
                            if signal_key not in sent_signals:
                                t1 = event.get('T1', [{}])[0].get('Nm', 'T1')
                                t2 = event.get('T2', [{}])[0].get('Nm', 'T2')
                                
                                comment = await get_ai_prediction(f"{t1}-{t2}, счет {s1}:{s2}", found_algo)
                                
                                msg = (f"🚨 **СИГНАЛ: {found_algo}**\n"
                                       f"🏆 {league}\n"
                                       f"⚔️ **{t1} — {t2}**\n"
                                       f"📊 Счет: `{s1}:{s2}`\n"
                                       f"⏱ Время: `{minute}' мин`\n\n"
                                       f"{comment}")

                                await bot.send_message(CHANNEL_ID, msg)
                                sent_signals.add(signal_key)
                                logger.info(f"Отправлен матч: {t1}-{t2}")
                                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Ошибка диспетчера: {e}")

async def main():
    while True:
        await check_logic()
        await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())
