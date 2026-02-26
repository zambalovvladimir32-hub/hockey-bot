import asyncio
import aiohttp
import os
import re
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

# Используем альтернативный "зеркальный" адрес, который реже блокируют
URL = "https://m.flashscore.com.ua/x/feed/proxy-direct"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "x-referer": "https://m.flashscore.com.ua/",
    "Origin": "https://m.flashscore.com.ua"
}

sent_signals = set()

async def get_ai_analysis(match_text):
    try:
        res = await gpt_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": f"Хоккей {match_text}. Прогноз на голы в 10 словах."}],
            max_tokens=40
        )
        return res.choices[0].message.content
    except:
        return "ИИ ждет результативный период!"

async def check():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            # Запрашиваем хоккей (f:8), лайв (p:1)
            async with session.get(URL, params={'f': '8', 'p': '1', 't': '1'}, timeout=15) as resp:
                if resp.status != 200:
                    logger.error(f"Код ошибки: {resp.status}")
                    return
                
                raw_data = await resp.text()
                # Если данных нет, Flashscore пришлет пустую строку или ошибку
                if not raw_data or 'AA÷' not in raw_data:
                    return

                matches = raw_data.split('~')
                for m in matches:
                    if 'AA÷' not in m: continue
                    
                    # Парсим данные через регулярки
                    try:
                        mid = re.search(r'AA÷([^¬]+)', m).group(1)
                        if mid in sent_signals: continue
                        
                        home = re.search(r'AE÷([^¬]+)', m).group(1)
                        away = re.search(r'AF÷([^¬]+)', m).group(1)
                        h_score = re.search(r'AG÷([^¬]+)', m).group(1)
                        a_score = re.search(r'AH÷([^¬]+)', m).group(1)
                        league = re.search(r'ZA÷([^¬]+)', m).group(1)
                        
                        analysis = await get_ai_analysis(f"{home}-{away}")
                        
                        msg = (f"🏒 **LIVE: {league}**\n\n"
                               f"⚔️ **{home} — {away}**\n"
                               f"📊 Счет: `{h_score}:{a_score}`\n\n"
                               f"🤖 {analysis}")
                        
                        await bot.send_message(CHANNEL_ID, msg)
                        sent_signals.add(mid)
                    except:
                        continue

        except Exception as e:
            logger.error(f"Ошибка в Amvera: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🛠 **Amvera: Прямой поиск матчей запущен.**\nИгнорирую фильтры, ищу всё, что в лайве!")
    while True:
        await check()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
