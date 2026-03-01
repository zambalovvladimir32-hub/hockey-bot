import asyncio, os, logging
from aiogram import Bot
from curl_cffi.requests import AsyncSession

# Настройка логов для Railway
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeyFinal_v38.5")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

# Твой прокси: http://логин:пароль@ip:порт
PROXY_URL = "http://Mr6scU:pCWpeD@196.19.10.101:8000"

class HockeyLogic:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo",
            "Referer": "https://www.flashscore.ru/",
            "x-requested-with": "XMLHttpRequest",
        }
        self.sent_cache = {}

    async def get_stats(self, session, m_id):
        """Запрос статистики матча через прокси"""
        url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1"
        try:
            # Имитируем реальный браузер (impersonate) через прокси
            r = await session.get(url, headers=self.headers, proxy=PROXY_URL, impersonate="chrome120", timeout=20)
            data = r.text
            
            if "¬" not in data:
                # Если всё еще 6556 байт, значит прокси не пустили или он перегружен
                logger.warning(f"⚠️ Проблема с данными (len={len(data)}) для матча {m_id}")
                return None

            parts = data.split("¬")
            stats = {"shots": 0, "pen": 0}
            for i, p in enumerate(parts):
                # Ищем Броски (SOG) или Удары
                if any(x in p for x in ["Броски", "SOG", "Удары в створ"]):
                    try:
                        stats["shots"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                    except: pass
                # Ищем Штрафное время (ПИМ)
                if any(x in p for x in ["ПИМ", "Штраф", "PM"]):
                    try:
                        stats["pen"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                    except: pass
            return stats
        except Exception as e:
            logger.error(f"🌐 Ошибка прокси: {e}")
            return None

    async def run(self):
        logger.info("🚀 Бот запущен! Используем прокси 196.19.10.101")
        async with AsyncSession() as session:
            while True:
                try:
                    # 1. Получаем список всех LIVE матчей
                    r = await session.get("https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", headers=self.headers, proxy=PROXY_URL, impersonate="chrome120")
                    
                    # 2. Фильтруем: только перерыв (AC÷46) и только после 1-го периода (нет BC÷)
                    matches = [m for m in r.text.split('~AA÷')[1:] if "AC÷46" in m and "BC÷" not in m]
                    
                    if matches:
                        logger.info(f"🔎 Найдено игр в перерыве: {len(matches)}")

                    for m_block in matches:
                        m_id = m_block.split('¬')[0]
                        if m_id in self.sent_cache: continue

                        h_team = m_block.split('AE÷')[1].split('¬')[0]
                        a_team = m_block.split('AF÷')[1].split('¬')[0]
                        
                        try:
                            h_score = int(m_block.split('AG÷')[1].split('¬')[0])
                            a_score = int(m_block.split('AH÷')[1].split('¬')[0])
                        except: continue

                        # 3. Фильтр счета: Сумма голов <= 1
                        if (h_score + a_score) <= 1:
                            logger.info(f"📊 Проверяю статистику: {h_team} - {a_team}")
                            res = await self.get_stats(session, m_id)
                            
                            if res:
                                # 4. Фильтр активности: Броски >= 11 ИЛИ Штраф >= 4
                                if res['shots'] >= 11 or res['pen'] >= 4:
                                    msg = (f"🏒 **{h_team} {h_score}:{a_score} {a_team}**\n"
                                           f"⏱ *Перерыв после 1-го периода*\n\n"
                                           f"🎯 Броски: `{res['shots']}`\n"
                                           f"⚖️ Штраф: `{res['pen']} мин`\n\n"
                                           f"🔗 [Открыть матч](https://www.flashscore.ru/match/{m_id})")
                                    
                                    await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                    logger.info(f"✅ СИГНАЛ ОТПРАВЛЕН: {h_team}")
                                    # Кэшируем на 2 часа, чтобы не дублировать
                                    self.sent_cache[m_id] = asyncio.get_event_loop().time()
                            
                    # Очистка кэша старых матчей
                    now = asyncio.get_event_loop().time()
                    self.sent_cache = {k: v for k, v in self.sent_cache.items() if now - v < 7200}
                    
                    await asyncio.sleep(45) # Проверка каждые 45 секунд
                except Exception as e:
                    logger.error(f"Ошибка цикла: {e}")
                    await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(HockeyLogic().run())
