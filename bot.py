import asyncio
import aiohttp
import os
import logging
import google.generativeai as genai
from aiogram import Bot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Настройка Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

bot = Bot(token=TOKEN)

# Глобальный API Livescore (Хоккей)
URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/8"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}

sent_matches = set()

async def get_ai_analysis(match_name, score):
    try:
        # Короткий запрос для скорости
        prompt = f"Хоккей {match_name}, счет {score}. Прогноз на голы (5 слов)."
        response = await asyncio.to_thread(model.generate_content, prompt)
        return f"🤖 {response.text.strip()}"
    except:
        return "🤖 Анализ: Ожидается активная игра."

async def check_hockey():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(URL, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    stages = data.get('Stages', [])
                    
                    for stage in stages:
                        league = stage.get('Snm', 'HOCKEY')
                        events = stage.get('Events', [])
                        
                        for event in events:
                            eid = event.get('Eid')
                            
                            # Если матч новый — обрабатываем
                            if eid not in sent_matches:
                                home = event.get('T1', [{}])[0].get('Nm', 'Команда 1')
                                away = event.get('T2', [{}])[0].get('Nm', 'Команда 2')
                                h_score = event.get('Tr1', '0')
                                a_score = event.get('Tr2', '0')
                                status = event.get('Eps', 'LIVE')

                                analysis = await get_ai_analysis(f"{home}-{away}", f"{h_score}:{a_score}")

                                msg = (f"🏒 **{league}**\n"
                                       f"⚔️ **{home} — {away}**\n"
                                       f"📊 Счет: `{h_score}:{a_score}` ({status})\n"
                                       f"{analysis}")

                                try:
                                    await bot.send_message(CHANNEL_ID, msg)
                                    sent_matches.add(eid)
                                    # Крошечная пауза, чтобы Telegram не забанил за спам
                                    await asyncio.sleep(0.5) 
                                except Exception as e:
                                    logger.error(f"Ошибка отправки: {e}")
                else:
                    logger.error(f"Ошибка API: {resp.status}")
        except Exception as e:
            logger.error(f"Ошибка сети: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🔥 **БЕЗЛИМИТНЫЙ РЕЖИМ: ВКЛЮЧЕН**\nТеперь собираю вообще все матчи из лайва!")
    while True:
        await check_hockey()
        # Проверка каждые 30 секунд для максимального охвата
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())
