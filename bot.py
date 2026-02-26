import asyncio
import aiohttp
import os
import logging
import google.generativeai as genai
from aiogram import Bot

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Переменные
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Настройка Google Gemini (Бесплатный ИИ)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

bot = Bot(token=TOKEN)

URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/8"
sent_matches = set()

async def get_free_ai_analysis(match_name, score):
    """Получает анализ от бесплатного Google Gemini"""
    try:
        prompt = f"Ты хоккейный аналитик. Матч {match_name}, счет {score}. Дай короткий прогноз на тотал больше 4.5 (макс 10 слов)."
        response = model.generate_content(prompt)
        return f"🤖 **ИИ:** {response.text.strip()}"
    except Exception as e:
        logger.error(f"Ошибка Gemini: {e}")
        return "📊 **Прогноз:** Ожидается активная игра и борьба за инициативу."

async def check_hockey():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(URL, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for stage in data.get('Stages', []):
                        league = stage.get('Snm', '').upper()
                        # Убираем киберхоккей
                        if any(x in league for x in ['NHL 24', 'CYBER', 'SHORT']): continue

                        for event in stage.get('Events', []):
                            eid = event.get('Eid')
                            if eid in sent_matches: continue

                            home = event.get('T1', [{}])[0].get('Nm', 'Команда 1')
                            away = event.get('T2', [{}])[0].get('Nm', 'Команда 2')
                            score = f"{event.get('Tr1', '0')}:{event.get('Tr2', '0')}"
                            
                            # Бесплатный анализ
                            analysis = await get_free_ai_analysis(f"{home}-{away}", score)

                            msg = (f"🏒 **МАТЧ В ЛАЙВЕ: {league}**\n\n"
                                   f"⚔️ **{home} — {away}**\n"
                                   f"📊 Текущий счет: `{score}`\n\n"
                                   f"{analysis}")

                            await bot.send_message(CHANNEL_ID, msg)
                            sent_matches.add(eid)
                            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Ошибка: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🆓 **Бот запущен на БЕСПЛАТНОМ ИИ (Google Gemini).**\nБольше никаких лимитов и оплат!")
    while True:
        await check_hockey()
        await asyncio.sleep(120)

if __name__ == "__main__":
    # Перед запуском нужно установить библиотеку: pip install google-generativeai
    asyncio.run(main())
