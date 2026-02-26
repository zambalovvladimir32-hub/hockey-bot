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
    now_chita = datetime.now(timezone.utc) + timedelta(hours=9)
    # Работаем почти всегда, когда есть игры
    if not (datetime.strptime("09:00", "%H:%M").time() <= now_chita.time() or now_chita.time() <= datetime.strptime("03:00", "%H:%M").time()):
        return

    today = (datetime.now(timezone.utc) + timedelta(hours=3)).strftime('%Y-%m-%d')
    url = f"https://{HOST}/games?date={today}"
    
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        try:
            async with session.get(url, headers=HEADERS) as resp:
                data = await resp.json()
                games = data.get('response', [])
                
                for game in games:
                    gid = game['id']
                    if gid in sent_signals: continue
                    
                    # 1. ПРОВЕРКА ЛИГИ (Обязательно)
                    league_id = game.get('league', {}).get('id')
                    if league_id not in ALLOWED_LEAGUES:
                        continue
                    
                    status_short = game['status']['short']
                    scores = game['scores']
                    h_s = scores.get('home', 0) if scores.get('home') is not None else 0
                    a_s = scores.get('away', 0) if scores.get('away') is not None else 0
                    total_goals = h_s + a_s
                    
                    # ГИБКИЙ ФИЛЬТР (Сработает, если выполнено ХОТЯ БЫ ОДНО из условий)
                    is_p1 = status_short in ['P1', 'IP', 'INT'] # Идет 1-й период или перерыв
                    is_low_score = total_goals <= 1             # Счет 0:0 или 1:0
                    
                    # Если лига наша И (идет 1-й период ИЛИ счет маленький)
                    if is_p1 or (status_short in ['P2', 'P3'] and total_goals == 0):
                        teams = f"{game['teams']['home']['name']} — {game['teams']['away']['name']}"
                        league_name = game['league']['name']
                        
                        logger.info(f"ГИБКИЙ СИГНАЛ: {teams} (Счет: {h_s}:{a_s}, Статус: {status_short})")
                        
                        gpt_res, grok_res = await get_ai_analysis(teams, f"{h_s}:{a_s}", league_name, game['status']['long'])
                        
                        msg = (
                            f"🏒 **ПОТЕНЦИАЛЬНЫЙ МАТЧ**\n\n"
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
            logger.error(f"Ошибка: {e}")

async def main():
    logger.info("Бот запущен. Гибкий фильтр (1-й период ИЛИ сухой счет) активен.")
    while True:
        await check_games()
        await asyncio.sleep(180)

if __name__ == "__main__":
    asyncio.run(main())
