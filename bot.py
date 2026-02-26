import asyncio
import aiohttp
import os
import logging
from google import genai  # Новая библиотека
from aiogram import Bot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Данные из Amvera
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Новый клиент без ошибок 404
client = genai.Client(api_key=GEMINI_KEY)
bot = Bot(token=TOKEN)

URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/8"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

sent_signals = set()

async def get_ai_comment(match_info, algo_name):
    try:
        # Новый формат запроса к Gemini
        response = client.models.generate_content(
            model="gemini-1.5-flash", 
            contents=f"Ты каппер. Стратегия: {algo_name}. Матч: {match_info}. Совет в 5 словах."
        )
        return f"🤖 {response.text.strip()}"
    except:
        return "🤖 Анализ: Ожидается реализация."

async def check_logic():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(URL, timeout=10) as resp:
                if resp.status != 200: return
                data = await resp.json()
                for stage in data.get('Stages', []):
                    for event in stage.get('Events', []):
                        eid = event.get('Eid')
                        period = event.get('Eps') 
                        try: min_ = int(event.get('Emm', 0))
                        except: min_ = 0
                        s1, s2 = int(event.get('Tr1', 0)), int(event.get('Tr2', 0))

                        # ТВОИ АЛГОРИТМЫ
                        found = None
                        # 1. Засуха
                        if period == '1ST' and 12 <= min_ <= 17 and ((s1==0 and s2==0) or (s1==1 and s2==0) or (s1==0 and s2==1)):
                            found = "ЗАСУХА 1-Й ПЕР"
                        # 2. Гол во 2-м
                        elif period == '2ND' and 21 <= min_ <= 30:
                            found = "ГОЛ ВО 2-М ПЕРИОДЕ"
                        # 3. Камбэк
                        elif period == '2ND' and (abs(s1-s2) in [1, 2]) and s1+s2 < 5:
                            found = "ОЖИДАЕМ КАМБЭК"

                        if found:
                            key = f"{eid}_{found}"
                            if key not in sent_signals:
                                t1, t2 = event['T1'][0]['Nm'], event['T2'][0]['Nm']
                                comment = await get_ai_comment(f"{t1}-{t2}", found)
                                msg = f"🚨 **{found}**\n🏒 {t1} — {t2}\n📊 Счет: `{s1}:{s2}` ({min_} мин)\n\n{comment}"
                                await bot.send_message(CHANNEL_ID, msg)
                                sent_signals.add(key)
                                logger.info(f"Сигнал отправлен: {t1}-{t2}")
        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}")

async def main():
    while True:
        await check_logic()
        await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())
