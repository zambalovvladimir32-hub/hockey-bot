import asyncio
import os
import logging
import random
from aiogram import Bot
from curl_cffi.requests import AsyncSession

# Настройка логов для панели Railway
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("HockeyGhost")

# Данные из переменных окружения Railway
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL") # Твой прокси (http://user:pass@ip:port)
bot = Bot(token=TOKEN)

class FlashscoreGhost:
    def __init__(self):
        # Заголовки как у реального браузера Chrome
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "x-fsign": "SW9D1eZo",
            "Referer": "https://www.flashscore.ru/",
            "Origin": "https://www.flashscore.ru",
            "X-Requested-With": "XMLHttpRequest"
        }
        self.sent_cache = {}

    async def get_match_stats(self, session, m_id):
        """Получение статистики бросков и штрафов по ID матча"""
        url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1"
        try:
            # Используем chrome120 для обхода TLS-защиты
            resp = await session.get(url, headers=self.headers, impersonate="chrome120", timeout=15)
            if "¬" in resp.text:
                data = resp.text
                stats = {"shots": 0, "pen": 0}
                parts = data.split("¬")
                for i, p in enumerate(parts):
                    # Ищем ключевые слова статистики
                    if any(x in p for x in ["Броски", "Удары", "SOG"]):
                        try:
                            stats["shots"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                        except: pass
                    if any(x in p for x in ["ПИМ", "Штраф", "PM"]):
                        try:
                            stats["pen"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                        except: pass
                return stats
        except Exception as e:
            logger.error(f"⚠️ Ошибка парсинга матча {m_id}: {e}")
        return None

    async def run(self):
        logger.info("🚀 === v37.1 GHOST-CHROME СТАРТОВАЛ ===")
        
        # Настройка прокси, если он указан
        proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
        if proxies:
            logger.info(f"🌐 Использую прокси: {PROXY_URL[:20]}...")
        
        async with AsyncSession(proxies=proxies) as session:
            while True:
                try:
                    # 1. Запрос списка LIVE матчей (Хоккей)
                    list_url = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
                    r = await session.get(list_url, headers=self.headers, impersonate="chrome120")
                    
                    # Фильтруем матчи в перерыве (статус AC÷46)
                    matches = [m for m in r.text.split('~AA÷')[1:] if "AC÷46" in m]
                    logger.info(f"🔎 Найдено игр в перерыве: {len(matches)}")

                    for m_block in matches:
                        try:
                            m_id = m_block.split('¬')[0]
                            if m_id in self.sent_cache: continue

                            h_team = m_block.split('AE÷')[1].split('¬')[0]
                            a_team = m_block.split('AF÷')[1].split('¬')[0]

                            logger.info(f"📊 Проверяю: {h_team} - {a_team}")
                            stats = await self.get_match_stats(session, m_id)

                            if stats:
                                logger.info(f"📈 Данные получены: Броски {stats['shots']}, ПИМ {stats['pen']}")
                                # Условие отправки (например, 11+ бросков)
                                if stats["shots"] >= 11:
                                    text = (f"🏒 **{h_team} — {a_team}**\n"
                                           f"━━━━━━━━━━━━\n"
                                           f"🎯 Броски (всего): `{stats['shots']}`\n"
                                           f"⚖️ Штраф (ПИМ): `{stats['pen']} мин`\n"
                                           f"━━━━━━━━━━━━\n"
                                           f"🔗 [Открыть матч](https://www.flashscore.ru/match/{m_id})")
                                    
                                    await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")
                                    logger.info(f"✅ Сигнал отправлен в канал!")
                                    self.sent_cache[m_id] = True
                            
                            await asyncio.sleep(random.uniform(2, 4)) # Пауза, чтобы не забанили
                        except Exception as e:
                            logger.error(f"Ошибка внутри блока матча: {e}")

                    logger.info("😴 Ожидание следующей проверки (60 сек)...")
                    await asyncio.sleep(60) 
                except Exception as e:
                    logger.error(f"❌ Критическая ошибка цикла: {e}")
                    await asyncio.sleep(30)

if __name__ == "__main__":
    try:
        asyncio.run(FlashscoreGhost().run())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
