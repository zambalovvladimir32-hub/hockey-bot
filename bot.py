import os
import asyncio
import aiohttp
import logging
from aiogram import Bot

# Настройка логов, чтобы видеть, что происходит
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

async def get_hockey_live():
    # Пробуем достучаться до фида, который видит ВСЕ лиги
    url = "https://d.flashscore.com/x/feed/f_4_0_2_ru-ru_1"
    headers = {
        "x-fsign": "SW9D1eZo", # Ключ из Perplexity (может протухнуть, но пока пробуем)
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    logger.error(f"Flashscore отдал ошибку: {resp.status}")
                    return []
                
                text = await resp.text()
                # Разрезаем этот текстовый винегрет на отдельные матчи
                raw_matches = text.split('~AA÷')
                live_games = []

                for block in raw_matches[1:]: # Первый блок всегда мусорный
                    try:
                        # Вытаскиваем названия команд и счет
                        # Это упрощенный парсинг "грязного" текста Flashscore
                        parts = block.split('¬')
                        data = {}
                        for p in parts:
                            if '÷' in p:
                                key, val = p.split('÷', 1)
                                data[key] = val
                        
                        t1 = data.get('AE', '???') # Хозяева
                        t2 = data.get('AF', '???') # Гости
                        s1 = data.get('AG', '0')   # Счет 1
                        s2 = data.get('AH', '0')   # Счет 2
                        status = data.get('ER', 'LIVE') # Период
                        
                        # Если это наш Норильск или любой матч во 2-м периоде
                        if "2" in status or "NORILSK" in t1.upper():
                            live_games.append(f"🏒 {t1} {s1}:{s2} {t2}\n⏱ Статус: {status}")
                    except:
                        continue
                
                return live_games
        except Exception as e:
            logger.error(f"Ошибка сети: {e}")
            return []

async def main():
    logger.info("🚀 Бот-сканер запущен!")
    while True:
        games = await get_hockey_live()
        
        if games:
            # Склеиваем топ-10 игр, чтобы не спамить по одному сообщению
            report = "🏆 **LIVE ХОККЕЙ (ВСЕ ЛИГИ)**\n\n" + "\n\n".join(games[:10])
            try:
                await bot.send_message(CHANNEL_ID, report, parse_mode="Markdown")
                logger.info("Сигнал отправлен в канал.")
            except Exception as e:
                logger.error(f"Ошибка отправки в ТГ: {e}")
        else:
            logger.info("На линии пока тихо...")

        # Ждем 1 минуту перед следующей проверкой
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
