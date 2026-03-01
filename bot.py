import asyncio, os, logging
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeyBlackBox_v38.0")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

class HockeyLogic:
    def __init__(self):
        # Обновленные, более "человечные" заголовки
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.flashscore.ru/",
            "x-fsign": "SW9D1eZo", # Попробуем оставить, но добавим доп. параметры
            "x-requested-with": "XMLHttpRequest",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        self.sent_cache = {}

    async def get_stats(self, session, m_id):
        url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1"
        try:
            r = await session.get(url, headers=self.headers, impersonate="chrome120", timeout=12)
            data = r.text
            
            if "¬" not in data:
                # ВЫВОДИМ В ЛОГ, ЧТО ИМЕННО ПРИСЛАЛ СЕРВЕР (первые 150 символов)
                preview = data[:150].replace('\n', ' ')
                logger.warning(f"⛔️ БЛОК ИЛИ ОШИБКА (len={len(data)}): {preview}")
                return None

            parts = data.split("¬")
            stats = {"shots": 0, "pen": 0}
            for i, p in enumerate(parts):
                if any(x in p for x in ["Броски", "SOG", "Удары в створ"]):
                    stats["shots"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                if any(x in p for x in ["ПИМ", "Штраф", "PM"]):
                    stats["pen"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
            return stats
        except Exception as e:
            logger.error(f"Ошибка соединения: {e}")
            return None

    async def run(self):
        logger.info("🚀 v38.0: ПОПЫТКА ПРОРЫВА БЛОКИРОВКИ")
        async with AsyncSession() as session:
            while True:
                try:
                    # Проверяем список матчей
                    r = await session.get("https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", headers=self.headers, impersonate="chrome120")
                    # Если даже список не грузится - мы в бане по IP
                    if "~AA÷" not in r.text:
                        logger.error(f"IP ЗАБЛОКИРОВАН (Длина ответа списка: {len(r.text)})")
                        await asyncio.sleep(60)
                        continue

                    matches = [m for m in r.text.split('~AA÷')[1:] if "AC÷46" in m]
                    logger.info(f"🔎 В перерыве: {len(matches)} игр. Проверяю статистику...")

                    for m_block in matches:
                        m_id = m_block.split('¬')[0]
                        if m_id in self.sent_cache or "BC÷" in m_block: continue

                        h_team = m_block.split('AE÷')[1].split('¬')[0]
                        a_team = m_block.split('AF÷')[1].split('¬')[0]
                        
                        try:
                            h_score = int(m_block.split('AG÷')[1].split('¬')[0])
                            a_score = int(m_block.split('AH÷')[1].split('¬')[0])
                        except: h_score, a_score = 0, 0

                        if (h_score + a_score) <= 1:
                            res = await self.get_stats(session, m_id)
                            if res:
                                logger.info(f"✅ УСПЕХ! {h_team} - Броски: {res['shots']}")
                                if res['shots'] >= 11 or res['pen'] >= 4:
                                    msg = (f"🏒 **{h_team} {h_score}:{a_score} {a_team}**\n"
                                           f"🎯 Броски: `{res['shots']}` | ⚖️ Штраф: `{res['pen']} мин`\n"
                                           f"🔗 [Матч](https://www.flashscore.ru/match/{m_id})")
                                    await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                    self.sent_cache[m_id] = asyncio.get_event_loop().time()
                            
                    await asyncio.sleep(45)
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
                    await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(HockeyLogic().run())
