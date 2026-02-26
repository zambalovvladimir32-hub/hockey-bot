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

async def get_ai_analysis(teams, score, league):
    prompt = f"Хоккей. 1-й период. Матч: {teams} ({league}). Счет: {score}. Оцени вероятность ТБ 4.5. Один вердикт (15 слов)."
    async def call_ai(client, model):
        try:
            res = await client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}], max_tokens=100)
            return res.choices[0].message.content
        except: return "Анализ временно недоступен."
    return await asyncio.gather(call_ai(gpt_client, "gpt-4o"), call_ai(grok_client, "grok-beta"))

async def check_games():
    now_chita = datetime.now(timezone.utc) + timedelta(hours=9)
    current_time = now_chita.time()
    start_time = datetime.strptime("16:20", "%H:%M").time()
    end_time = datetime.strptime("03:00", "%H:%M").time()
    
    if not (start_time <= current_time or current_time <= end_time):
        return

    today = (datetime.now(timezone.utc) + timedelta(hours=3)).strftime('%Y-%m-%d')
    url = f"https://{HOST}/games?date={today}"
    
    # Таймауты для защиты от зависания
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(url, headers=HEADERS) as resp:
                if resp.status == 429:
                    logger.warning("Слишком много запросов (429). Ждем...")
                    return
                
                data = await resp.json()
                games = data.get('response', [])
                
                for game in games:
                    gid = game['id']
                    if gid in sent_signals: continue
                    
                    if game.get('league', {}).get('id') not in ALLOWED_LEAGUES:
                        continue
                    
                    status_short = game['status']['short']
                    # Ловим P1 и перерыв (IP/INT)
                    if status_short in ['P1', 'IP', 'INT']:
                        scores = game['scores']
                        h_s = scores.get('home', 0) or 0
                        a_s = scores.get('away', 0) or 0
                        
                        if (h_s + a_s) <= 1:
                            teams = f"{game['teams']['home']['name']} — {game['teams']['away']['name']}"
                            league_name = game['league']['name']
                            display_status = "1-й период" if status_short == 'P1' else "ПЕРЕРЫВ (после 1-го)"
                            
                            logger.info(f"СИГНАЛ: {teams} ({display_status})")
                            gpt_res, grok_res = await get_ai_analysis(teams, f"{h_s}:{a_s}", league_name)
                            
                            msg = (
                                f"🏒 **СИГНАЛ: МОНИТОРИНГ**\n\n"
                                f"⚔️ {teams}\n"
                                f"🏆 {league_name}\n"
                                f"⏰ Статус: {display_status}\n"
                                f"📊 Счет: {h_s}:{a_s}\n\n"
                                f"🤖 **GPT-4o:** {gpt_res}\n\n"
                                f"🦾 **GROK:** {grok_res}"
                            )
                            await bot.send_message(CHANNEL_ID, msg)
                            sent_signals.add(gid)

        except aiohttp.ClientConnectorError:
            logger.error("Ошибка подключения к серверу API. Повтор через 5 минут.")
        except Exception as e:
            logger.error(f"Ошибка цикла: {e}")

async def main():
    logger.info("Бот запущен. Расширенный мониторинг активен!")
    while True:
        await check_games()
        await asyncio.sleep(300) # Пауза 5 минут для обхода лимитов

if __name__ == "__main__":
    asyncio.run(main())
