import asyncio
import os
import logging
import re
import sys
from aiogram import Bot
# Магическая библиотека для обхода блокировок Cloudflare
from curl_cffi.requests import AsyncSession

# Настройка логирования в консоль Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Данные из переменных окружения Railway
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

# Настройки Flashscore
URL = "https://d.flashscore.ru/x/feed/f_4_0_2_ru-ru_1"
# Ключ может меняться сайтом, если перестанет работать - нужно обновить x-fsign
FSIGN = "SW9D1eZo" 

async def get_flashscore_data():
    """Запрос к Flashscore с имитацией реального браузера Chrome"""
    headers = {
        "x-fsign": FSIGN,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.flashscore.ru/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # impersonate="chrome120" заставляет сайт верить, что это человек
    async with AsyncSession(impersonate="chrome120") as session:
        try:
            resp = await session.get(URL, headers=headers, timeout=15)
            if resp.status_code == 200:
                logger.info("✅ Данные успешно скачаны")
                return resp.text
            else:
                logger.error(f"🚫 Ошибка Flashscore: {resp.status_code}")
                return None
        except Exception as e:
            logger.error(f"🔥 Ошибка сети: {e}")
            return None

def parse_games(raw_data):
    """Разбор сырых данных и фильтрация по стратегии (2-й период)"""
    if not raw_data:
        return []
    
    matches = []
    # Flashscore делит матчи маркером ~AA÷
    blocks = raw_data.split('~AA÷')
    
    for block in blocks[1:]:
        try:
            # Вытягиваем все теги из блока матча в словарь
            res = dict(re.findall(r'(\w+)÷([^¬]+)', block))
            
            home = res.get('AE', '???')  # Хозяева
            away = res.get('AF', '???')  # Гости
            s1 = res.get('AG', '0')      # Счет хозяев
            s2 = res.get('AH', '0')      # Счет гостей
            
            # Собираем все поля статуса (ER, ST, EP) в одну строку
            status = (res.get('ER', '') + res.get('ST', '') + res.get('EP', '')).upper()
            
            # Маркеры 2-го периода (Цифры, Кириллица, Латиница)
            triggers = ["2", "P2", "П2", "2ND", "ВТОР", "ВТО", "S2"]
            is_2nd_period = any(x in status for x in triggers)
            
            # Отдельно ловим Норильск (на любом языке)
            is_target_team = "норильск" in home.lower() or "норильск" in away.lower() or "norilsk" in home.lower()

            if is_2nd_period or is_target_team:
                # Формируем красивое сообщение
                msg = (f"🏒 **{home} {s1}:{s2} {away}**\n"
                       f"⏱ Статус: {status if status else '2-й период'}")
                matches.append(msg)
                logger.info(f"🎯 Нашел подходящий матч: {home} - {away} ({status})")
        except Exception as e:
            continue
            
    return matches

async def main():
    logger.info("🚀 БОТ-СКАНЕР ЗАПУЩЕН!")
    # Приветственное сообщение в канал
    try:
        await bot.send_message(CHANNEL_ID, "✅ **Бот онлайн.** Начинаю поиск 2-х периодов...")
    except Exception as e:
        logger.error(f"Не удалось отправить старт в ТГ: {e}")

    while True:
        raw = await get_flashscore_data()
        
        if raw:
            games = parse_games(raw)
            if games:
                # Отправляем найденные матчи одним сообщением (максимум 10 штук)
                report = "🥅 **LIVE: ИДЕТ 2-й ПЕРИОД**\n\n" + "\n\n".join(games[:10])
                try:
                    await bot.send_message(CHANNEL_ID, report, parse_mode="Markdown")
                    logger.info("✅ Сигнал отправлен в Telegram")
                except Exception as e:
                    logger.error(f"Ошибка отправки сообщения: {e}")
            else:
                logger.info("...сканирую... пока 2-х периодов не найдено")
        
        # Проверка каждую минуту
        await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
