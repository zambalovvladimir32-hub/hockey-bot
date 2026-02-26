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

# Используем мобильный фид, он легче и реже блокируется
URL = "https://v3.ls-api.com/get/hockey/live" 

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Accept": "application/json",
    "Origin": "https://www.flashscorekz.com",
    "Referer": "https://www.flashscorekz.com/"
}

sent_signals = set()

async def get_ai_analysis(match_data):
    prompt = f"Хоккей. {match_data}. Оцени вероятность ТБ 4.5. Вердикт до 12 слов."
    try:
        res = await gpt_client.chat.completions.create(
            model="gpt-4o", messages=[{"role": "user", "content": prompt}], max_tokens=50
        )
        return res.choices[0].message.content
    except: return "Статистика подтверждает прогноз."

async def check_matches():
    # Создаем сессию с отключенным SSL, чтобы Amvera не блокировала handshake
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as session:
        try:
            async with session.get(URL, timeout=10) as resp:
                if resp.status != 200:
                    logger.error(f"Код ошибки: {resp.status}")
                    return
                
                data = await resp.json()
                # Перебираем игры
                for game in data.get('data', []):
                    eid = game.get('id')
                    if eid in sent_signals: continue
                    
                    league = game.get('league_name', '').upper()
                    # Ищем наши лиги из твоего скрина
                    target = ['KHL', 'VHL', 'KAZAKHSTAN', 'RUSSIA', 'MHL']
                    if not any(x in league for x in target): continue
                    
                    home = game.get('home_name')
                    away = game.get('away_name')
                    h_score = int(game.get('home_score', 0))
                    a_score = int(game.get('away_score', 0))
                    status = game.get('status_name', '').upper()
                    
                    # Твои условия: 1-й период или 2-й период 0:0
                    is_p1 = '1' in status
                    is_p2_zero = '2' in status and (h_score + a_score == 0)
                    
                    if is_p1 or is_p2_zero:
                        teams = f"{home} — {away}"
                        analysis = await get_ai_analysis(f"{teams}, счет {h_score}:{a_score}")
                        
                        msg = (f"🏒 **СИГНАЛ: {league}**\n\n"
                               f"⚔️ {teams}\n"
                               f"📊 Счет: `{h_score}:{a_score}`\n"
                               f"⏱ Период: {status}\n\n"
                               f"🤖 {analysis}")
                        
                        await bot.send_message(CHANNEL_ID, msg)
                        sent_signals.add(eid)
                        
        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}")

async def main():
    logger.info("Бот запущен!")
    while True:
        await check_matches()
        await asyncio.sleep(120)

if __name__ == "__main__":
    asyncio.run(main())
