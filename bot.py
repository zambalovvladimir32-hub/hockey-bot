import asyncio
import aiohttp
import os
import logging
from aiogram import Bot
from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=TOKEN)
gpt_client = AsyncOpenAI(api_key=OPENAI_KEY)

# Прямой рабочий шлюз
URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/8"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"}

async def get_ai_analysis(match_text):
    try:
        res = await gpt_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": f"Хоккей {match_text}. Краткий прогноз на ТБ 4.5 до 10 слов."}],
            max_tokens=40
        )
        return res.choices[0].message.content
    except: return "Анализ временно недоступен."

async def force_check_all():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(URL, timeout=15) as resp:
                if resp.status != 200:
                    await bot.send_message(CHANNEL_ID, f"❌ Ошибка шлюза: {resp.status}")
                    return
                
                data = await resp.json()
                stages = data.get('Stages', [])
                
                if not stages:
                    await bot.send_message(CHANNEL_ID, "📭 В лайве сейчас нет ни одного хоккейного матча в мире. Ждем утренние игры.")
                    return

                # Берем максимум 3 любых матча, которые идут прямо сейчас
                found = 0
                for stage in stages:
                    league = stage.get('Snm', 'Лига')
                    for event in stage.get('Events', []):
                        if found >= 3: break
                        
                        home = event.get('T1', [{}])[0].get('Nm', 'Команда А')
                        away = event.get('T2', [{}])[0].get('Nm', 'Команда Б')
                        score = f"{event.get('Tr1', 0)}:{event.get('Tr2', 0)}"
                        status = event.get('Eps', 'LIVE')
                        
                        analysis = await get_ai_analysis(f"{home}-{away}")
                        
                        msg = (f"🎯 **ТЕСТОВЫЙ ЗАХВАТ: {league}**\n\n"
                               f"⚔️ **{home} — {away}**\n"
                               f"📊 Текущий счет: `{score}`\n"
                               f"⏱ Статус: `{status}`\n\n"
                               f"🤖 **ИИ:** {analysis}")
                        
                        await bot.send_message(CHANNEL_ID, msg)
                        found += 1
                    if found >= 3: break

        except Exception as e:
            logger.error(f"Ошибка: {e}")

if __name__ == "__main__":
    # Запускаем проверку один раз прямо при старте
    asyncio.run(force_check_all())
