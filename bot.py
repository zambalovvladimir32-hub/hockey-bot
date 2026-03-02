import asyncio, os, logging
from aiogram import Bot
from curl_cffi.requests import AsyncSession
from urllib.parse import quote

# Настройка логов для максимальной ясности
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeySenior_v42.1")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
API_TOKEN = os.getenv("SCRAPER_TOKEN") 

bot = Bot(token=TOKEN)

class HockeyLogic:
    def __init__(self):
        self.sent_cache = {}

    async def fetch_via_api(self, session, target_url, use_render=True):
        """
        Используем render=True по умолчанию, так как Flashscore 
        явно требует выполнения JS для отдачи данных.
        """
        if not API_TOKEN:
            logger.error("🚨 КРИТИЧЕСКАЯ ОШИБКА: Переменная SCRAPER_TOKEN пуста в Railway!")
            return None

        # Формируем URL запроса к Scrape.do
        api_url = f"https://api.scrape.do?token={API_TOKEN.strip()}&url={quote(target_url)}&render=true"
        
        try:
            r = await session.get(api_url, timeout=60)
            
            if r.status_code == 401:
                logger.error("❌ ОШИБКА 401: Твой API TOKEN не подходит! Проверь его в настройках Railway.")
                return None
            
            if r.status_code == 429:
                logger.error("⏳ ОШИБКА 429: Закончились лимиты на бесплатном тарифе API.")
                return None

            if "¬" in r.text:
                return r.text
            
            logger.warning(f"⚠️ Ответ получен (код {r.status_code}), но данных внутри нет. Размер: {len(r.text)}")
            return None
                
        except Exception as e:
            logger.error(f"💥 Ошибка соединения: {e}")
            return None

    async def get_stats(self, session, m_id):
        url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1"
        data = await self.fetch_via_api(session, url)
        
        if data:
            parts = data.split("¬")
            stats = {"shots": 0, "pen": 0}
            for i, p in enumerate(parts):
                if any(x in p for x in ["Броски", "SOG", "Удары в створ"]):
                    try: stats["shots"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                    except: pass
                if any(x in p for x in ["ПИМ", "Штраф", "PM"]):
                    try: stats["pen"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                    except: pass
            return stats
        return None

    async def run(self):
        logger.info("🦾 СТАРШАЯ МОДЕЛЬ В ДЕЛЕ. БОТ ЗАПУЩЕН.")
        async with AsyncSession() as session:
            while True:
                try:
                    list_url = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
                    list_data = await self.fetch_via_api(session, list_url)

                    if list_data:
                        # Ищем только матчи в перерыве (AC÷46) после 1-го периода
                        matches = [m for m in list_data.split('~AA÷')[1:] if "AC÷46" in m and "BC÷" not in m]
                        logger.info(f"🔎 Найдено подходящих игр: {len(matches)}")

                        for m_block in matches:
                            m_id = m_block.split('¬')[0]
                            if m_id in self.sent_cache: continue

                            h_team = m_block.split('AE÷')[1].split('¬')[0]
                            a_team = m_block.split('AF÷')[1].split('¬')[0]
                            
                            try:
                                h_score = int(m_block.split('AG÷')[1].split('¬')[0])
                                a_score = int(m_block.split('AH÷')[1].split('¬')[0])
                            except: continue

                            # Фильтр: не более 1 гола
                            if (h_score + a_score) <= 1:
                                logger.info(f"📊 Запрашиваю статистику для: {h_team} - {a_team}")
                                res = await self.get_stats(session, m_id)
                                
                                if res:
                                    # Фильтр: 11+ бросков или 4+ мин штрафа
                                    if res['shots'] >= 11 or res['pen'] >= 4:
                                        msg = (f"🏒 **{h_team} {h_score}:{a_score} {a_team}**\n"
                                               f"🎯 Броски: `{res['shots']}` | ⚖️ Штраф: `{res['pen']} мин`\n\n"
                                               f"🔗 [Матч](https://www.flashscore.ru/match/{m_id})")
                                        await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                        self.sent_cache[m_id] = asyncio.get_event_loop().time()
                                        logger.info(f"💰 СИГНАЛ ОТПРАВЛЕН: {h_team}")
                    
                    await asyncio.sleep(180) # Проверка каждые 3 минуты (бережем лимиты API)
                except Exception as e:
                    logger.error(f"⚠️ Ошибка в главном цикле: {e}")
                    await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(HockeyLogic().run())
