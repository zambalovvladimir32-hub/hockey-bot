import asyncio
import aiohttp
import logging
import os
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher
from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ключи из переменных Amvera
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
SPORTRADAR_KEY = os.getenv("API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
GROK_KEY = os.getenv("GROK_API_KEY")

gpt_client = AsyncOpenAI(api_key=OPENAI_KEY)
grok_client = AsyncOpenAI(api_key=GROK_KEY, base_url="https://api.x.ai/v1")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# URL для LIVE матчей
URL = f"https://api.sportradar.us/hockey/trial/v2/en/scheduled/live/summary.json?api_key={SPORTRADAR_KEY}"
sent_signals = set()

async def get_ai_analysis(teams, score, league):
    prompt = f"Матч: {teams} ({league}). Текущий счет {score}. Дай краткий прогноз на тотал матча (1 предложение)."
    async def call_ai(client, model):
        try:
            res = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100
            )
            return res.choices[0].message.content
        except: return "Анализ недоступен."
    return await asyncio.gather(call_ai(gpt_client, "gpt-4o"), call_ai(grok_client, "grok-beta"))

async def check_games():
    logger.info("ЗАПУСК ТЕСТОВОЙ ПРОВЕРКИ (ПУБЛИКАЦИЯ ВСЕХ LIVE ИГР)...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(URL) as resp:
                if resp.status != 200:
                    logger.error(f"Ошибка Sportradar: {resp.status}")
                    return
                data = await resp.json()
        except Exception as e:
            logger.error(f"Ошибка сети: {e}")
            return

    summaries = data.get('summaries', [])
    if not summaries:
        logger.info("Сейчас нет активных LIVE-матчей в базе.")
        return

    for game in summaries:
        event = game.get('sport_event', {})
        sid = event.get('id')
        
        # Чтобы не спамить одним и тем же матчем по кругу
        if sid in sent_signals: continue

        status = game.get('sport_event_status', {})
        teams = f"{event['competitors'][0]['name']} — {event['competitors'][1]['name']}"
        league = event.get('tournament', {}).get('name', 'Хоккей')
        h_score = status.get('home_score', 0)
        a_score = status.get('away_score', 0)
        period = status.get('period', 'N/A')

        logger.info(f"Тестируем отправку: {teams}")

        gpt_res, grok_res = await get_ai_analysis(teams, f"{h_score}:{a_score}", league)

        msg = (
            f"🧪 **ТЕСТОВЫЙ ВЫВОД LIVE-МАТЧА**\n\n"
            f"⚔️ {teams}\n"
            f"🏆 {league}\n"
            f"⏰ Период: {period} | Счет: {h_score}:{a_score}\n\n"
            f"🤖 GPT: {gpt_res}\n"
            f"🦾 GROK: {grok_res}\n"
        )
        
        try:
            await bot.send_message(chat_id=CHANNEL_ID, text=msg)
            sent_signals.add(sid) # Помечаем как отправленный
            logger.info(f"Успешно отправлено: {teams}")
        except Exception as e:
            logger.error(f"Ошибка отправки: {e}")

async def main():
    logger.info("Бот запущен в ТЕСТОВОМ режиме (публикует всё подряд)")
    while True:
        await check_games()
        await asyncio.sleep(60) # Проверка каждую минуту для теста

if __name__ == "__main__":
    asyncio.run(main())
