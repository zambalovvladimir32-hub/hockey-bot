import asyncio
import aiohttp
import os
import logging
import re
from aiogram import Bot
from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=TOKEN)
gpt_client = AsyncOpenAI(api_key=OPENAI_KEY)

# Прямой мобильный поток данных
URL = "https://m.flashscore.kz/x/feed/proxy-direct"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "x-referer": "https://m.flashscore.kz/",
    "x-requested-with": "XMLHttpRequest"
}

sent_signals = set()

async def get_ai_analysis(match_text):
    try:
        res = await gpt_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": f"Хоккей {match_text}. Дай дерзкий прогноз на тотал больше в 10 словах."}],
            max_tokens=50
        )
        return res.choices[0].message.content
    except: return "ИИ видит здесь много заброшенных шайб!"

async def check_all_matches():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            # Запрашиваем вообще все хоккейные лайв-события (f:8 - хоккей, p:1 - лайв)
            async with session.get(URL, params={'f': '8', 'p': '1', 't': '1'}, timeout=15) as resp:
                raw_data = await resp.text()
                
                # Разбиваем поток на отдельные матчи
                sections = raw_data.split('~')
                
                for section in sections:
                    if 'AA÷' not in section: continue
                    
                    # Извлекаем данные через регулярки или поиск (это надежнее для Flashscore)
                    mid = re.search(r'AA÷([^¬]+)', section)
                    home = re.search(r'AE÷([^¬]+)', section)
                    away = re.search(r'AF÷([^¬]+)', section)
                    h_score = re.search(r'AG÷([^¬]+)', section)
                    a_score = re.search(r'AH÷([^¬]+)', section)
                    league = re.search(r'ZA÷([^¬]+)', section)
                    
                    if mid:
                        match_id = mid.group(1)
                        if match_id in sent_signals: continue
                        
                        h_team = home.group(1) if home else "Команда А"
                        a_team = away.group(1) if away else "Команда Б"
                        score = f"{h_score.group(1) if h_score else 0}:{a_score.group(1) if a_score else 0}"
                        lg_name = league.group(1) if league else "HOCKEY LIVE"
                        
                        # Делаем анализ и шлем сразу!
                        analysis = await get_ai_analysis(f"{h_team} - {a_team}")
                        
                        msg = (f"🏒 **LIVE: {lg_name}**\n\n"
                               f"⚔️ **{h_team} — {a_team}**\n"
                               f"📊 Текущий счет: `{score}`\n\n"
                               f"🤖 **ВЕРДИКТ:** {analysis}")
                        
                        await bot.send_message(CHANNEL_ID, msg)
                        sent_signals.add(match_id)
                        logger.info(f"Отправлен: {h_team}")

        except Exception as e:
            logger.error(f"Ошибка: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🚀 **БЕЗЛИМИТНЫЙ РЕЖИМ ВКЛЮЧЕН!**\nТеперь кидаю вообще все лайв-матчи без разбора.")
    while True:
        await check_all_matches()
        await asyncio.sleep(60) # Проверка каждую минуту

if __name__ == "__main__":
    asyncio.run(main())
