import asyncio, os, logging, random
from aiogram import Bot
from curl_cffi.requests import AsyncSession

# Настройка логов, чтобы видеть всё в панели Railway
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeyGhost")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL") # Твой прокси из Вирджинии
bot = Bot(token=TOKEN)

class FlashscoreGhost:
    def __init__(self):
        # Заголовки, которые делают нас "человеком"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Accept": "*/*",
            "x-fsign": "SW9D1eZo",
            "Referer": "https://www.flashscore.ru/",
            "Origin": "https://www.flashscore.ru"
        }
        self.sent_cache = {}

    async def get_match_stats(self, session, m_id):
        # Запрос к внутреннему API статистики
        url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1"
        try:
            # impersonate="safari_ios_16_0" обходит защиту TLS
            resp = await session.get(url, headers=self.headers, impersonate="safari_ios_16_0", timeout=10)
            if "¬" in resp.text:
                data = resp.text
                stats = {"shots": 0, "pen": 0}
                parts = data.split("¬")
                for i, p in enumerate(parts):
                    if any(x in p for x in ["Броски", "Удары", "SOG"]):
                        # Суммируем броски обеих команд
                        stats["shots"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                    if any(x in p for x in ["ПИМ", "Штраф", "PM"]):
                        # Суммируем штрафное время
                        stats["pen"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                return stats
        except Exception as e:
            logger.error(f"Ошибка парсинга {m_id}: {e}")
        return None

    async def run(self):
        logger.info("=== v37.0 GHOST ENGINE STARTED (NO BROWSER) ===")
        proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
        
        async with AsyncSession(proxies=proxies) as session:
            while True:
                try:
                    # 1. Получаем список всех матчей (Live)
                    # f_4_0_3 - это хоккей, live
                    list_url = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
                    r = await session.get(list_url, headers=self.headers, impersonate="safari_ios_16_0")
                    
                    # Ищем матчи в перерыве (код статуса AC÷46)
                    matches = [m for m in r.text.split('~AA÷')[1:] if "AC÷46" in m]
                    logger.info(f"🔎 Найдено игр в перерыве: {len(matches)}")

                    for m_block in matches:
                        m_id = m_block.split('¬')[0]
                        if m_id in self.sent_cache: continue

                        h_team = m_block.split('AE÷')[1].split('¬')[0]
                        a_team = m_block.split('AF÷')[1].split('¬')[0]

                        logger.info(f"📊 Проверяю статистику: {h_team} - {a_team}")
                        stats = await self.get_match_stats(session, m_id)

                        if stats and stats["shots"] >= 11:
                            text = (f"🏒 **{h_team} — {a_team}**\n\n"
                                   f"🎯 Броски (общие): `{stats['shots']}`\n"
                                   f"⚖️ Штраф (ПИМ): `{stats['pen']} мин`\n\n"
                                   f"🔗 [Открыть матч](https://www.flashscore.ru/match/{m_id})")
                            
                            await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")
                            logger.info(f"✅ Сигнал отправлен для {m_id}")
                            self.sent_cache[m_id] = True
                        
                        await asyncio.sleep(2) # Пауза между матчами

                    await asyncio.sleep(60) # Пауза между проверками списка
                except Exception as e:
                    logger.error(f"Главный цикл: {e}")
                    await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(FlashscoreGhost().run())
