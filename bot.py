import asyncio
import aiohttp
import os
import logging
import random
from aiogram import Bot
from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=TOKEN)
gpt_client = AsyncOpenAI(api_key=OPENAI_KEY)

# Скрытый мобильный фид (меньше защиты, чем на сайте)
URL = "https://v3.ls-api.com/get/hockey/live"

# Расширенный список User-Agent для ротации (чтобы не забанили)
USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

sent_signals = set()

async def get_ai_analysis(match_info):
    try:
        res = await gpt_client.chat.completions.create(
            model="gpt-4o", 
            messages=[{"role": "user", "content": f"Хоккей. {match_info}. Прогноз на ТБ 4.5 в 10 словах."}],
            max_tokens=40
        )
        return res.choices[0].message.content
    except: return "ИИ рекомендует присмотреться к ТБ."

async def run_monitor():
    # Ротация заголовков
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json",
        "Referer": "https://www.flashscore.kz/",
        "Origin": "https://www.flashscore.kz"
    }
    
    # Решаем проблему SSL и закрытых сессий (всегда создаем новую)
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        try:
            async with session.get(URL, timeout=20) as resp:
                if resp.status != 200:
                    logger.error(f"Сайт ответил кодом {resp.status}")
                    return

                data = await resp.json()
                games = data.get('data', [])
                
                # Твои лиги из скринов (Салават, Трактор, Горняк и т.д.)
                target_leagues = ['KHL', 'VHL', 'KAZAKHSTAN', 'MHL', 'RUSSIA']
                
                for g in games:
                    eid = g.get('id')
                    if eid in sent_signals: continue
                    
                    league = g.get('league_name', '').upper()
                    if not any(x in league for x in target_leagues): continue
                    
                    # Данные матча
                    home = g.get('home_name')
                    away = g.get('away_name')
                    h_score = int(g.get('home_score', 0))
                    a_score = int(g.get('away_score', 0))
                    status = g.get('status_name', '').upper()
                    
                    # Условия: 1-й период ИЛИ 2-й период со счетом 0:0
                    is_p1 = '1' in status
                    is_p2_zero = '2' in status and (h_score + a_score == 0)
                    
                    if is_p1 or is_p2_zero:
                        match_text = f"{home} - {away}, счет {h_score}:{a_score}"
                        analysis = await get_ai_analysis(match_text)
                        
                        final_msg = (
                            f"🏒 **СИГНАЛ: {league}**\n\n"
                            f"⚔️ **{home} — {away}**\n"
                            f"📊 Счет: `{h_score}:{a_score}`\n"
                            f"⏱ Статус: `{status}`\n\n"
                            f"🤖 **ИИ:** {analysis}"
                        )
                        
                        await bot.send_message(CHANNEL_ID, final_msg)
                        sent_signals.add(eid)
                        logger.info(f"Отправлен сигнал по {home}")

        except Exception as e:
            logger.error(f"Ошибка в работе: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🛡 **Бот запущен в режиме обхода блокировок.**")
    while True:
        await run_monitor()
        # Проверяем каждые 4 минуты, чтобы не привлекать внимание защиты
        await asyncio.sleep(240)

if __name__ == "__main__":
    asyncio.run(main())
