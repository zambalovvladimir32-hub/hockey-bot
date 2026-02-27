import asyncio
import aiohttp
import os
import logging
import sys
from aiogram import Bot
from google import genai

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

bot = Bot(token=TOKEN)
# Инициализация ИИ (если есть ключ)
ai_client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/0"
sent_signals = set()

async def get_ai_prediction(teams, score, period):
    if not ai_client: return "🤖 ИИ готов к анализу."
    try:
        prompt = f"Хоккей. {teams}, счет {score}, идет {period} период. Дай краткий прогноз на тотал (5-7 слов)."
        res = ai_client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        return f"🤖 AI: {res.text.strip()}"
    except: return "🤖 AI: Ожидается динамичная концовка."

async def check_matches():
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_4_1 like Mac OS X)",
        "X-Requested-With": "com.livescore.app"
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(URL, timeout=15) as resp:
                data = await resp.json()
                found_any = 0
                
                for stage in data.get('Stages', []):
                    league = stage.get('Snm', 'Хоккей')
                    for event in stage.get('Events', []):
                        found_any += 1
                        t1, t2 = event['T1'][0]['Nm'], event['T2'][0]['Nm']
                        status = event.get('Eps', 'LIVE') # Статус (1ST, 2ND, 3RD, FT)
                        s1, s2 = event.get('Tr1', '0'), event.get('Tr2', '0')
                        
                        logger.info(f"НАЙДЕНО: {t1} {s1}:{s2} {t2} (Статус: {status})")

                        # Уникальный ключ: команда + счет + период
                        key = f"{t1}_{s1}_{s2}_{status}"
                        
                        if key not in sent_signals:
                            # Помечаем стратегию, если это 2-й период
                            strat_tag = "🔥 СТРАТЕГИЯ (2-й ПЕР)" if status == '2ND' else "🏒 LIVE-ОБЗОР"
                            
                            ai_text = await get_ai_prediction(f"{t1}-{t2}", f"{s1}:{s2}", status)
                            
                            msg = (f"{strat_tag}\n"
                                   f"🏆 {league}\n
