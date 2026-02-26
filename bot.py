import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher
from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ключи
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
SPORTRADAR_KEY = os.getenv("API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
GROK_KEY = os.getenv("GROK_API_KEY")

gpt_client = AsyncOpenAI(api_key=OPENAI_KEY)
grok_client = AsyncOpenAI(api_key=GROK_KEY, base_url="https://api.x.ai/v1")

bot = Bot(token=TOKEN)
dp = Dispatcher()

URL = f"https://api.sportradar.us/hockey/trial/v2/en/scheduled/live/summary.json?api_key={SPORTRADAR_KEY}"
sent_signals = set()

async def get_ai_analysis(teams, score, league, shots):
    prompt = (
        f"Матч: {teams} ({league}). 1-й период, счет {score}, бросков в створ: {shots}. "
        f"Оцени вероятность ТБ 3.5 на весь матч. Дай краткий вердикт (1-2 предложения)."
    )
    async def call_ai(client, model):
        try:
            res = await client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": "Ты хоккейный аналитик."},
                          {"role": "user", "content": prompt}],
                max_tokens=150
            )
            return res.choices[0].message.content
        except: return "Анализ временно недоступен."

    return await asyncio.gather(call_ai(gpt_client, "gpt-4o"), call_ai(grok_client, "grok-beta"))

async def check_games():
    # Работа по МСК: 16:20 - 03:00 (Чита: 22:20 - 09:00)
    now = datetime.now(timezone.utc) + timedelta(hours=3)
    if not (now.hour >= 16 or now.hour < 3):
        return

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(URL) as resp:
                if resp.status != 200: return
                data = await resp.json()
        except: return

    for game in data.get('summaries', []):
        sid = game.get('sport_event', {}).get('id')
        if sid in sent_signals: continue

        status = game.get('sport_event_status', {})
        if status.get('period') == 1:
            h, a = status.get('home_score', 0), status.get('away_score', 0)
            
            # Условие по счету
            if (h + a) <= 1:
                # Фильтр по броскам (Теперь 8!)
                total_shots = status.get('home_shots_on_goal', 0) + status.get('away_shots_on_goal', 0)
                
                if total_shots >= 8:
                    event = game.get('sport_event', {})
                    teams = f"{event['competitors'][0]['name']} — {event['competitors'][1]['name']}"
                    league = event.get('tournament', {}).get('name', 'Хоккей')

                    gpt_res, grok_res = await get_ai_analysis(teams, f"{h}:{a}", league, total_shots)

                    msg = (
                        f"🏒 **СИГНАЛ: ТОТАЛ МАТЧА БОЛЬШЕ 3.5**\n\n"
                        f"⚔️ {teams}\n"
                        f"🏆 {league}\n"
                        f"⏰ 1-й период | Счет: {h}:{a}\n"
                        f"📊 Бросков в створ: {total_shots} (Активная игра!)\n\n"
                        f"🤖 **GPT-4o:** {gpt_res}\n\n"
                        f"🦾 **GROK:** {grok_res}\n\n"
                        f"📈 *Ставка: ТБ 3.5 на весь матч*"
                    )
                    
                    await bot.send_message(chat_id=CHANNEL_ID, text=msg)
                    sent_signals.add(sid)

async def main():
    while True:
        await check_games()
        await asyncio.sleep(300)

if __name__ == "__main__":
    asyncio.run(main())
