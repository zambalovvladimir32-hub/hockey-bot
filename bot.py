import asyncio
import os
import logging
import sys
import random
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

# Меняем URL на альтернативный (f_4_0_3 вместо f_4_0_2)
URL = "https://d.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
FSIGN = "SW9D1eZo" 

async def get_flashscore_data():
    headers = {
        "x-fsign": FSIGN,
        "x-flashscore-icp": "1",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.flashscore.ru/",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    
    async with AsyncSession(impersonate="chrome120") as session:
        try:
            # Добавляем случайную задержку перед запросом, чтобы не выглядеть как робот
            await asyncio.sleep(random.uniform(1, 5))
            resp = await session.get(URL, headers=headers, timeout=20)
            
            if resp.status_code == 200 and len(resp.text) > 100:
                return resp.text
            
            logger.warning(f"⚠️ Получен подозрительный ответ: {len(resp.text) if resp.text else 0} байт")
            return None
        except Exception as e:
            logger.error(f"🔥 Ошибка сети: {e}")
            return None

def parse_games(raw_data):
    if not raw_data: return []
    matches = []
    blocks = raw_data.split('~AA÷')
    
    for block in blocks[1:]:
        try:
            # Ищем команды
            home = block.split('AE÷')[1].split('¬')[0] if 'AE÷' in block else "???"
            away = block.split('AF÷')[1].split('¬')[0] if 'AF÷' in block else "???"
            
            # Статус периода (ищем цифру 2 в ключевых позициях)
            # В хоккее часто идет TT÷2 (текущий период) или NS÷2
            is_2nd = any(x in block for x in ['TT÷2', 'NS÷2', 'EP÷2', 'ST÷2', 'П2'])

            if is_2nd:
                s1 = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else "0"
                s2 = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else "0"
                matches.append(f"🏒 **{home} {s1}:{s2} {away}**\n⏱ Статус: 2-й период")
                logger.info(f"🎯 Поймал: {home} - {away}")
        except:
            continue
    return matches

async def main():
    logger.info("🚀 БОТ ПЕРЕЗАПУЩЕН С НОВЫМ ФИДОМ")
    while True:
        raw = await get_flashscore_data()
        if raw:
            logger.info(f"📦 Данные получены! Размер: {len(raw)} байт. Парсим...")
            games = parse_games(raw)
            if games:
                report = "🥅 **LIVE: ОБНАРУЖЕН 2-Й ПЕРИОД**\n\n" + "\n\n".join(games[:10])
                await bot.send_message(CHANNEL_ID, report, parse_mode="Markdown")
                logger.info("📡 Сигнал в Telegram!")
            else:
                logger.info("⏸ 2-х периодов в этом пакете данных нет.")
        else:
            logger.error("📭 Не удалось получить данные (пустой ответ).")
        
        # Увеличим паузу, чтобы нас меньше банили
        await asyncio.sleep(90)

if __name__ == "__main__":
    asyncio.run(main())
