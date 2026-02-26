import asyncio
import aiohttp
import os
import logging
from aiogram import Bot
from openai import AsyncOpenAI

# Настройка логирования для Amvera
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Загрузка твоих ключей из настроек Amvera
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=TOKEN)
gpt_client = AsyncOpenAI(api_key=OPENAI_KEY)

# Источник данных (Flashscore/Livescore), который прошел проверку связи
HOCKEY_URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/8"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Origin": "https://www.livescore.com",
    "Referer": "https://www.livescore.com/"
}

# Список ID матчей, по которым уже был сигнал
sent_signals = set()

async def get_ai_analysis(teams, score, status):
    """Запрос к GPT-4o для оценки вероятности ТБ 4.5"""
    prompt = (f"Хоккей. Статус: {status}. Команды: {teams}. Счет: {score}. "
              f"Оцени вероятность тотала больше 4.5. Дай краткий вердикт как каппер (до 15 слов).")
    try:
        response = await gpt_client.chat.completions.create(
            model="gpt-4o", 
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Ошибка GPT: {e}")
        return "Нейросеть анализирует движение коэффициентов..."

async def monitor():
    """Проверка матчей в лайве"""
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(HOCKEY_URL, timeout=15) as resp:
                if resp.status != 200:
                    logger.warning(f"Источник временно недоступен: {resp.status}")
                    return
                
                data = await resp.json()
                stages = data.get('Stages', [])
                
                for stage in stages:
                    league_name = stage.get('Snm', '').upper()
                    
                    # ФИЛЬТР: Только наши лиги
                    allowed = ['RUSSIA', 'KHL', 'VHL', 'MHL', 'SLOVAKIA', 'BELARUS', 'KAZAKHSTAN']
                    if not any(x in league_name for x in allowed):
                        continue
                    
                    for event in stage.get('Events', []):
                        eid = event.get('Eid')
                        if eid in sent_signals:
                            continue
                        
                        # Информация о матче
                        home = event.get('T1', [{}])[0].get('Nm', 'Хозяева')
                        away = event.get('T2', [{}])[0].get('Nm', 'Гости')
                        h_score = int(event.get('Tr1', 0))
                        a_score = int(event.get('Tr2', 0))
                        total = h_score + a_score
                        status = event.get('Eps', '').upper()
                        
                        # --- ТВОЯ ЛОГИКА СИГНАЛА ---
                        # 1. Если 1-й период и забито до 3 шайб
                        is_p1 = '1ST' in status or '1-Й' in status
                        # 2. Если 2-й период и счет 0:0
                        is_p2_zero = ('2ND' in status or '2-Й' in status) and total == 0
                        
                        if (is_p1 and total <= 3) or is_p2_zero:
                            teams_str = f"{home} — {away}"
                            analysis = await get_ai_analysis(teams_str, f"{h_score}:{a_score}", status)
                            
                            signal_text = (
                                f"🏒 **НОВЫЙ СИГНАЛ: ТОТАЛ БОЛЬШЕ**\n\n"
                                f"⚔️ **{teams_str}**\n"
                                f"🏆 Лига: {league_name}\n"
                                f"📊 Счет: `{h_score}:{a_score}`\n"
                                f"⏱ Период: `{status}`\n\n"
                                f"🤖 **Мнение ИИ:** _{analysis}_"
                            )
                            
                            await bot.send_message(CHANNEL_ID, signal_text, parse_mode="Markdown")
                            sent_signals.add(eid)
                            logger.info(f"Сигнал отправлен: {teams_str}")
                            
        except Exception as e:
            logger.error(f"Ошибка в мониторинге: {e}")

async def main():
    logger.info("Бот запущен!")
    # Отправляем приветствие в канал при старте
    try:
        await bot.send_message(CHANNEL_ID, "✅ **Бот-аналитик успешно запущен.**\nМониторинг лиг РФ и Словакии активен.")
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение в канал: {e}")

    while True:
        await monitor()
        # Проверка раз в 3 минуты (чтобы не было бана от API)
        await asyncio.sleep(180)

if __name__ == "__main__":
    asyncio.run(main())
