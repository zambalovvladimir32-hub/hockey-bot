import asyncio, os, logging
from aiogram import Bot
from curl_cffi.requests import AsyncSession
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeySenior_v47.0")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ZENROWS_TOKEN = os.getenv("ZENROWS_TOKEN") 

bot = Bot(token=TOKEN)

class HockeyLogic:
    def __init__(self):
        self.sent_cache = {}

    async def fetch_zenrows(self, session, target_url, is_stats=False):
        if not ZENROWS_TOKEN:
            logger.error("🚨 ZENROWS_TOKEN пуст!")
            return None

        # Для статистики (is_stats=True) включаем самый мощный режим
        # Для списка матчей — режим попроще (экономим кредиты)
        params = f"apikey={ZENROWS_TOKEN.strip()}&url={quote(target_url)}&premium_proxy=true"
        if is_stats:
            params += "&js_render=true&wait_for_id=statistics-table-all" # Ждем именно таблицу статы
            
        api_url = f"https://api.zenrows.com/v1/?{params}"
        
        try:
            r = await session.get(api_url, timeout=60)
            if r.status_code == 200:
                return r.text
            logger.warning(f"⚠️ ZenRows статус {r.status_code} для {'статы' if is_stats else 'списка'}")
            return None
        except Exception as e:
            logger.error(f"💥 Ошибка API: {e}")
            return None

    async def parse_stats(self, data):
        """Разбираем кашу из символов в понятные цифры"""
        if not data or "¬" not in data: return None
        
        parts = data.split("¬")
        stats = {"shots": 0, "pen": 0}
        found = False

        for i, p in enumerate(parts):
            # Ищем маркеры статистики
            # SE÷Броски в створ, SG÷12 (хозяева), SH÷8 (гости)
            if any(x in p for x in ["Броски", "SOG", "Удары в створ"]):
                try:
                    stats["shots"] = int(parts[i+2].split("÷")[1]) + int(parts[i+3].split("÷")[1])
                    found = True
                except: pass
            if any(x in p for x in ["ПИМ", "Штраф", "PM"]):
                try:
                    stats["pen"] = int(parts[i+2].split("÷")[1]) + int(parts[i+3].split("÷")[1])
                    found = True
                except: pass
        
        return stats if found else None

    async def run(self):
        logger.info("🦾 СТАРШАЯ МОДЕЛЬ: v47.0 штурмует статистику...")
        async with AsyncSession() as session:
            while True:
                try:
                    # 1. Тянем список (без JS, дешево)
                    list_data = await self.fetch_zenrows(session, "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", is_stats=False)

                    if list_data:
                        matches = [m for m in list_data.split('~AA÷')[1:] if "AC÷46" in m]
                        logger.info(f"🔎 В перерыве: {len(matches)} игр")

                        for m_block in matches:
                            m_id = m_block.split('¬')[0]
                            if m_id in self.sent_cache: continue

                            h_score = int(m_block.split('AG÷')[1].split('¬')[0])
                            a_score = int(m_block.split('AH÷')[1].split('¬')[0])
                            
                            if (h_score + a_score) <= 1:
                                h_team = m_block.split('AE÷')[1].split('¬')[0]
                                logger.info(f"📊 Иду за статой для {h_team} (использую JS Render)...")
                                
                                # 2. Тянем стату (С JS РЕНДЕРОМ, ДОРОГО)
                                stat_raw = await self.fetch_zenrows(session, f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1", is_stats=True)
                                res = await self.parse_stats(stat_raw)
                                
                                if res:
                                    logger.info(f"✅ Данные пробиты! Броски: {res['shots']}, Штраф: {res['pen']}")
                                    if res['shots'] >= 11 or res['pen'] >= 4:
                                        a_team = m_block.split('AF÷')[1].split('¬')[0]
                                        msg = (f"🏒 **{h_team} {h_score}:{a_score} {a_team}**\n"
                                               f"🎯 Броски: `{res['shots']}` | ⚖️ Штраф: `{res['pen']} мин`")
                                        await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                        self.sent_cache[m_id] = True
                                else:
                                    logger.warning(f"⚪️ Статистика для {m_id} пока пуста (не прогрузилась на сайте)")

                    await asyncio.sleep(240)
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
                    await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(HockeyLogic().run())
