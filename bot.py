import asyncio, os, logging, random
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeyStealth_v38.1")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

class HockeyLogic:
    def __init__(self):
        # Расширенный список User-Agent для ротации
        self.ua_list = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ]
        self.sent_cache = {}

    def get_headers(self):
        return {
            "User-Agent": random.choice(self.ua_list),
            "Accept": "*/*",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.flashscore.ru/",
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "XMLHttpRequest",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }

    async def get_stats(self, session, m_id):
        url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1"
        try:
            # Делаем паузу перед запросом статы, чтобы не частить
            await asyncio.sleep(random.uniform(1.5, 3.0))
            r = await session.get(url, headers=self.get_headers(), impersonate="chrome120", timeout=15)
            data = r.text
            
            if "¬" not in data:
                logger.warning(f"⛔️ БЛОК (len={len(data)}) на матче {m_id}")
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
            logger.error(f"Ошибка парсинга {m_id}: {e}")
            return None

    async def run(self):
        logger.info("🕵️ v38.1: ВКЛЮЧЕН РЕЖИМ STEALTH")
        async with AsyncSession() as session:
            while True:
                try:
                    # Запрос списка матчей
                    r = await session.get("https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", headers=self.get_headers(), impersonate="chrome120")
                    
                    # Фильтр: только перерыв (AC÷46) и только после 1-го периода (нет BC÷)
                    matches = [m for m in r.text.split('~AA÷')[1:] if "AC÷46" in m and "BC÷" not in m]
                    
                    logger.info(f"🔎 Найдено {len(matches)} подходящих перерывов")

                    for m_block in matches:
                        m_id = m_block.split('¬')[0]
                        if m_id in self.sent_cache: continue

                        h_team = m_block.split('AE÷')[1].split('¬')[0]
                        a_team = m_block.split('AF÷')[1].split('¬')[0]
                        
                        try:
                            h_score = int(m_block.split('AG÷')[1].split('¬')[0])
                            a_score = int(m_block.split('AH÷')[1].split('¬')[0])
                        except: continue

                        # Фильтр счета: 0:0, 1:0, 0:1
                        if (h_score + a_score) <= 1:
                            logger.info(f"📊 Запрашиваю статику для {h_team} - {a_team}")
                            res = await self.get_stats(session, m_id)
                            
                            if res:
                                # Фильтр активности: броски >= 11 или штраф >= 4
                                if res['shots'] >= 11 or res['pen'] >= 4:
                                    msg = (f"🏒 **{h_team} {h_score}:{a_score} {a_team}**\n"
                                           f"🎯 Броски: `{res['shots']}` | ⚖️ Штраф: `{res['pen']} мин`\n"
                                           f"🔗 [Матч](https://www.flashscore.ru/match/{m_id})")
                                    await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                    self.sent_cache[m_id] = asyncio.get_event_loop().time()
                            
                    await asyncio.sleep(45)
                except Exception as e:
                    logger.error(f"Ошибка цикла: {e}")
                    await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(HockeyLogic().run())
