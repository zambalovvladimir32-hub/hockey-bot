import asyncio
import aiohttp
import os
import logging
import sys
from google import genai
from aiogram import Bot

# Настраиваем логи так, чтобы они летели прямо в консоль Amvera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Сразу пишем в лог, чтобы проверить запуск
print("!!! ПИТОН ЗАПУСТИЛ ФАЙЛ BOT.PY !!!")
logger.info("Бот начинает инициализацию...")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

try:
    client = genai.Client(api_key=GEMINI_KEY)
    bot = Bot(token=TOKEN)
    logger.info("Подключение к Telegram и Gemini — ОК")
except Exception as e:
    logger.error(f"Ошибка при старте: {e}")

URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/8"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

sent_signals = set()

async def get_ai_prediction(match_data, algo):
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=f"Ты каппер. Стратегия: {algo}. Матч: {match_data}. Дай совет в 5 словах."
        )
        return f"🤖 {response.text.strip()}"
    except Exception as e:
        logger.error(f"Ошибка ИИ: {e}")
        return "🤖 Анализ: Ожидается результативная игра."

async def check_logic():
    logger.info("--- ПРОВЕРКА МАТЧЕЙ (ПАРСИНГ) ---")
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(URL, timeout=15) as resp:
                if resp.status != 200:
                    logger.warning(f"Сервер Livescore ответил статусом: {resp.status}")
                    return
                
                data = await resp.json()
                logger.info(f"Данные получены. Обрабатываем лиги...")
                
                for stage in data.get('Stages', []):
                    for event in stage.get('Events', []):
                        eid = event.get('Eid')
                        period = event.get('Eps') 
                        try: min_ = int(event.get('Emm', 0))
                        except: min_ = 0
                        s1, s2 = int(event.get('Tr1', 0)), int(event.get('Tr2', 0))

                        found = None
                        if period == '1ST' and 12 <= min_ <= 17 and (s1+s2 <= 1):
                            found = "ЗАСУХА 1-Й ПЕР"
                        elif period == '2ND' and 21 <= min_ <= 30:
                            found = "ГОЛ ВО 2-М ПЕРИОДЕ"
                        elif period == '2ND' and (abs(s1-s2) in [1, 2]) and s1+s2 < 5:
                            found = "ОЖИДАЕМ КАМБЭК"

                        if found:
                            key = f"{eid}_{found}"
                            if key not in sent_signals:
                                t1, t2 = event['T1'][0]['Nm'], event['T2'][0]['Nm']
                                logger.info(f"НАЙДЕН МАТЧ: {t1}-{t2}. Запрашиваем ИИ...")
                                comment = await get_ai_prediction(f"{t1}-{t2}", found)
                                msg = f"🚨 **{found}**\n🏒 {t1} — {t2}\n📊 Счет: `{s1}:{s2}` ({min_} мин)\n\n{comment}"
                                await bot.send_message(CHANNEL_ID, msg)
                                sent_signals.add(key)
                                logger.info(f"СИГНАЛ ОТПРАВЛЕН В ТГ!")

        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}")

async def main():
    logger.info("Основной цикл запущен. Вхожу в режим ожидания матчей.")
    while True:
        await check_logic()
        await asyncio.sleep(40)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.critical(f"Критическая ошибка запуска: {e}")
