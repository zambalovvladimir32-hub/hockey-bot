import asyncio, os, logging, random
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeyHardStealth_v38.9")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL") 
bot = Bot(token=TOKEN)

class HockeyLogic:
    def __init__(self):
        # Максимально «человеческие» заголовки
        self.headers = {
            "accept": "*/*",
            "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "sec-ch-ua": '"Not(A:Bar";v="99", "Google Chrome";v="122", "Chromium";v="122"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "XMLHttpRequest",
            "Referer": "https://www.flashscore.ru/",
        }

    async def get_stats(self, session, m_id):
        url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1"
        try:
            # Используем impersonate="chrome110" и чистим куки перед каждым важным запросом
            r = await session.get(
                url, 
                headers=self.headers, 
                proxy=PROXY_URL, 
                impersonate="chrome110", 
                timeout=25
            )
            data = r.text
            
            if "¬" not in data:
                return f"БЛОК (len={len(data)})"

            parts = data.split("¬")
            stats = {"shots": 0, "pen": 0}
            for i, p in enumerate(parts):
                if any(x in p for x in ["Броски", "SOG", "Удары"]):
                    stats["shots"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                if any(x in p for x in ["ПИМ", "Штраф", "PM"]):
                    stats["pen"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
            return stats
        except Exception as e:
            return f"Ошибка: {e}"

    async def run(self):
        logger.info("🛡 Запуск v38.9: Глубокая маскировка")
        async with AsyncSession() as session:
            while True:
                try:
                    # Случайная пауза перед циклом (чтобы не было тайминга ровно в 45 сек)
                    await asyncio.sleep(random.randint(5, 15))
                    
                    r = await session.get(
                        "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", 
                        headers=self.headers, 
                        proxy=PROXY_URL, 
                        impersonate="chrome110"
                    )
                    
                    matches = [m for m in r.text.split('~AA÷')[1:] if "AC÷46" in m]
                    logger.info(f"🏟 Найдено в перерыве: {len(matches)}")

                    for m_block in matches:
                        m_id = m_block.split('¬')[0]
                        h_team = m_block.split('AE÷')[1].split('¬')[0]
                        a_team = m_block.split('AF÷')[1].split('¬')[0]
                        
                        # Небольшая пауза между запросами статы (имитация чтения)
                        await asyncio.sleep(random.uniform(1.5, 4.0))
                        
                        res = await self.get_stats(session, m_id)
                        logger.info(f"📊 {h_team} vs {a_team}: {res}")
                        
                        if isinstance(res, dict) and (res['shots'] >= 11 or res['pen'] >= 4):
                            # Проверяем счет (суммарно <= 1)
                            try:
                                h_score = int(m_block.split('AG÷')[1].split('¬')[0])
                                a_score = int(m_block.split('AH÷')[1].split('¬')[0])
                                if (h_score + a_score) <= 1:
                                    msg = (f"🏒 **{h_team} {h_score}:{a_score} {a_team}**\n"
                                           f"🎯 Броски: `{res['shots']}` | ⚖️ Штраф: `{res['pen']} мин`")
                                    await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                            except: pass

                    await asyncio.sleep(45)
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
                    await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(HockeyLogic().run())
