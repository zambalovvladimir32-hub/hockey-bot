import asyncio
import aiohttp
import os
import logging
from aiogram import Bot
from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=TOKEN)
gpt_client = AsyncOpenAI(api_key=OPENAI_KEY)

# Глобальный технический адрес (обычно не блокируется)
URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/8"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

sent_matches = set()

async def get_ai_analysis(match_name):
    try:
        res = await gpt_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": f"Хоккей. {match_name}. Прогноз на тотал больше 4.5. Вердикт до 10 слов."}],
            max_tokens=50
        )
        return res.choices[0].message.content
    except:
        return "Ожидается высокая результативность."

async def run_monitoring():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        while True:
            try:
                async with session.get(URL, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        stages = data.get('Stages', [])
                        
                        for stage in stages:
                            league = stage.get('Snm', 'Хоккей')
                            for event in stage.get('Events', []):
                                eid = event.get('Eid')
                                if eid in sent_matches: continue
                                
                                home = event.get('T1', [{}])[0].get('Nm', 'Команда 1')
                                away = event.get('T2', [{}])[0].get('Nm', 'Команда 2')
                                h_score = event.get('Tr1', '0')
                                a_score = event.get('Tr2', '0')
                                status = event.get('Eps', 'LIVE')
                                
                                analysis = await get_ai_analysis(f"{home} - {away}")
                                
                                msg = (f"🏒 **LIVE: {league}**\n\n"
                                       f"⚔️ **{home} — {away}**\n"
                                       f"📊 Счет: `{h_score}:{a_score}` ({status})\n\n"
                                       f"🤖 **GPT:** {analysis}")
                                
                                await bot.send_message(CHANNEL_ID, msg)
                                sent_matches.add(eid)
                                logger.info(f"Отправлен матч: {home}")
                    else:
                        logger.error(f"Ошибка сервера: {resp.status}")
            except Exception as e:
                logger.error(f"Ошибка цикла: {e}")
            
            await asyncio.sleep(60) # Проверка каждую минуту

async def main():
    try:
        await bot.send_message(CHANNEL_ID, "✅ **Бот запущен на Amvera!**\nИщу любые активные матчи...")
    except: pass
    await run_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
