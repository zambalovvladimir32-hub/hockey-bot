import asyncio
import aiohttp
import logging
import os
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher
from openai import AsyncOpenAI

# Настройка логирования
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

# ОБНОВЛЕННЫЙ URL ДЛЯ V4 (Global Ice Hockey Base)
URL = f"https://api.sportradar.us/hockey/trial/v4/en/games/live/summary.json?api_key={SPORTRADAR_KEY}"

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
        except Exception as e:
            logger.error(f"Ошибка AI ({model}): {e}")
            return "Анализ временно недоступен."
    
    return await asyncio.gather(call_ai(gpt_client, "gpt-4o"), call_ai(grok_client, "grok-beta"))

async def check_games():
    logger.info("--- ЗАПУСК ПРОВЕРКИ API V4 ---")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(URL) as resp:
                if resp.status == 403:
                    logger.error("ОШИБКА 403: Доступ запрещен. Проверь активацию ключа или лимиты тарифа.")
                    return
                if resp.status != 200:
                    logger.error(f"Ошибка Sportradar: {resp.status}")
                    text = await resp.text()
                    logger.error(f"Ответ сервера: {text}")
                    return
                
                data = await resp.json()
        except Exception as e:
            logger.error(f"Ошибка сети: {e}")
            return
