import asyncio
import aiohttp
import logging
import os
from datetime import datetime, timedelta, timezone
from aiogram import Bot
from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
API_KEY = os.getenv("FOOTBALL_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
GROK_KEY = os.getenv("GROK_API_KEY")

gpt_client = AsyncOpenAI(api_key=OPENAI_KEY)
grok_client = AsyncOpenAI(api_key=GROK_KEY, base_url="https://api.x.ai/v1")
bot = Bot(token=TOKEN)

HOST = 'v1.hockey.api-sports.io'
HEADERS = {'x-rapidapi-key': API_KEY, 'x-rapidapi-host': HOST}
ALLOWED_LEAGUES = [57, 40, 51, 41, 120, 110, 66, 114, 182, 185, 17]

sent_signals = set()

async def get_ai_analysis(teams, score, league, status):
    prompt = f"Хоккей. {status}. Матч: {teams} ({league}). Счет: {score}. Оцени вероятность ТБ 4.5. Один вердикт (15 слов)."
    async def call_ai(client, model):
        try:
            res = await client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}], max_tokens=100)
            return res.choices[0].message.content
        except: return "Анализ временно недоступен."
    return await asyncio.gather(call_ai(gpt_client, "gpt-4o"), call_ai(grok_client, "grok-beta"))

async def check_games():
    # Работа по Чите (UTC+9)
    now_chita = datetime.now(timezone.utc) + timedelta(hours=9)
    
    # Запрос игр за сегодня (с запасом по времени)
    today = (datetime.now(timezone.utc) + timedelta(hours=3)).strftime('%Y-%m-%d')
    url = f"https://{HOST}/games?date={today}"
    
    # Настройки для обхода Connection Reset
    connector = aiohttp.TCPConnector(ssl=False, keepalive_timeout=30)
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        try:
            async with session.get(url, headers=HEADERS) as resp:
                if resp.status != 200:
                    logger.error(f"Ошибка API: статус {resp.status}")
                    return

                data = await resp.json()
                games = data.get('response', [])
                
                for game in games:
                    gid = game['id']
                    if gid in sent_signals: continue
                    
                    # 1. ПРОВЕРКА ЛИГИ
                    l_id = game.get('league', {}).get('id')
                    if l_id not in ALLOWED_LEAGUES:
                        continue
                    
                    status_short = str(game['status']['short']).upper()
                    status_long = str(game['status']['long']).upper()
                    
                    # 2. ГИБКИЙ ФИЛЬТР СТАТУСА
                    # Ловим всё, что похоже на 1-й период или перерыв
                    is_p1 = any(x in status_short for x in ['P1', 'IP', 'INT', '1ST']) or "FIRST" in status_long
                    is_break = "INTERMISSION" in status_long or "ПЕРЕРЫВ" in status_long
                    
                    scores = game['scores']
                    h_s = scores.get('home', 0) if scores.get('home') is not None else 0
                    a_s = scores.get('away', 0) if scores.get('away') is not None else 0
                    
                    # Условие: Идет 1-й период/перерыв ИЛИ (идет 2-й период но счет 0:0)
                    if is_p1 or is_break or (status_short == 'P2' and (h_s + a_s) == 0):
                        teams = f"{game['teams']['home']['name']} — {game['teams']['away']['name']}"
                        league_name = game['league']['name']
                        
                        logger.info(f"СИГНАЛ: {teams} (Счет: {h_s}:{a_s}, Статус: {status_short})")
                        
                        gpt_res, grok_res = await get_ai_analysis(teams, f"{h_s}:{a_s}", league_name, status_long)
                        
                        msg = (
                            f"🏒 **LIVE: НАШ ХОККЕЙ**\n\n"
                            f"⚔️ {teams}\n"
                            f"🏆 {league_name}\n"
                            f"📊 Счет: {h_s}:{a_s}\n"
                            f"⏱ Статус: {game['status']['long']}\n\n"
                            f"🤖 GPT-4o: {gpt_res}\n"
                            f"🦾 GROK: {grok_res}"
                        )
                        await bot.send_message(CHANNEL_ID, msg)
                        sent_signals.add(gid)

        except Exception as e:
            logger.error(f"Ошибка в цикле: {e}")

async def main():
    logger.info("Бот запущен. Тотальный мониторинг РФ + Словакия.")
    while True:
        await check_games()
        # Пауза 4 минуты, чтобы API не сбрасывало соединение
        await asyncio.sleep(240)

if __name__ == "__main__":
    asyncio.run(main())
