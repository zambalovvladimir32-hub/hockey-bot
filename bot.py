import os
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher
from openai import AsyncOpenAI

# Настройка логирования для Amvera
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ключи из переменных окружения Amvera
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
SPORTRADAR_KEY = os.getenv("API_KEY")  # Ключ от Sportradar
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
GROK_KEY = os.getenv("GROK_API_KEY")

# Инициализация ИИ-клиентов
gpt_client = AsyncOpenAI(api_key=OPENAI_KEY)
grok_client = AsyncOpenAI(api_key=GROK_KEY, base_url="https://api.x.ai/v1")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Ссылка на Live-хоккей Sportradar (Trial v2)
URL = f"https://api.sportradar.us/hockey/trial/v2/en/scheduled/live/summary.json?api_key={SPORTRADAR_KEY}"

# Хранилище отправленных сигналов
sent_signals = set()

async def get_ai_analysis(teams, score, league, shots):
    """Параллельный опрос двух нейросетей"""
    prompt = (
        f"Анализируй хоккейный матч: {teams} ({league}). "
        f"1-й период, счет {score}, бросков в створ суммарно: {shots}. "
        f"Оцени вероятность ТБ 3.5 на весь матч. Дай краткий прогноз (1-2 предложения)."
    )
    
    async def call_ai(client, model):
        try:
            res = await client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": "Ты хоккейный аналитик-каппер."},
                          {"role": "user", "content": prompt}],
                max_tokens=150
            )
            return res.choices[0].message.content
        except Exception as e:
            return f"ИИ недоступен ({str(e)[:30]})"

    # Запускаем оба ИИ одновременно для скорости
    return await asyncio.gather(
        call_ai(gpt_client, "gpt-4o"),
        call_ai(grok_client, "grok-beta")
    )

async def check_games():
    # Работа по Москве: с 16:20 до 03:00 (Твой пояс Чита: 22:20 - 09:00)
    now = datetime.now(timezone.utc) + timedelta(hours=3)
    if not (now.hour >= 16 or now.hour < 3):
        logger.info("Бот в режиме ожидания (не рабочее время по МСК)")
        return

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(URL) as resp:
                if resp.status != 200:
                    logger.error(f"Ошибка Sportradar API: {resp.status}")
                    return
                data = await resp.json()
        except Exception as e:
            logger.error(f"Ошибка сети: {e}")
            return

    for game in data.get('summaries', []):
        sport_event = game.get('sport_event', {})
        game_id = sport_event.get('id')
        
        if game_id in sent_signals:
            continue

        status = game.get('sport_event_status', {})
        period = status.get('period')
        
        # Условие: 1-й период
        if period == 1:
            h = status.get('home_score', 0)
            a = status.get('away_score', 0)
            
            # Твои условия по счету: 0:0, 1:0 или 0:1
            if (h == 0 and a == 0) or (h == 1 and a == 0) or (h == 0 and a == 1):
                
                # Извлекаем броски в створ (Shots on Goal)
                h_shots = status.get('home_shots_on_goal', 0)
                a_shots = status.get('away_shots_on_goal', 0)
                total_shots = h_shots + a_shots
                
                # Твой фильтр: минимум 12 бросков (давление на ворота)
                if total_shots >= 12:
                    teams = f"{sport_event['competitors'][0]['name']} — {sport_event['competitors'][1]['name']}"
                    league = sport_event.get('tournament', {}).get('name', 'Хоккей')

                    logger.info(f"Найден матч: {teams} (Броски: {total_shots})")

                    # Получаем анализ от GPT и Grok
                    gpt_res, grok_res = await get_ai_analysis(teams, f"{h}:{a}", league, total_shots)

                    msg = (
                        f"🥅 **СИГНАЛ: ТОТАЛ МАТЧА БОЛЬШЕ 3.5**\n\n"
                        f"⚔️ {teams}\n"
                        f"🏆 {league}\n"
                        f"⏰ 1-й период | Счет: {h}:{a}\n"
                        f"📊 Броски в створ: {total_shots}\n\n"
                        f"🤖 **GPT-4o:** {gpt_res}\n\n"
                        f"🦾 **GROK (xAI):** {grok_res}\n\n"
                        f"📈 *Рекомендация: ТБ 3.5 на весь матч*"
                    )
                    
                    try:
                        await bot.send_message(chat_id=CHANNEL_ID, text=msg)
                        sent_signals.add(game_id)
                        logger.info(f"Сигнал по {teams} отправлен в канал")
                    except Exception as e:
                        logger.error(f"Ошибка отправки в Telegram: {e}")

async def main():
    logger.info("Бот (Sportradar + GPT + Grok) запущен и готов к работе!")
    while True:
        await check_games()
        # Проверка каждые 5 минут, чтобы не частить запросами к ИИ
        await asyncio.sleep(300)

if __name__ == "__main__":
    asyncio.run(main())
