import asyncio, os, logging, sys, time
from aiogram import Bot
from curl_cffi.requests import AsyncSession

# Настройка логов для Railway
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeySniperPro")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

# Список лиг (самые надежные)
STAT_LEAGUES = ["НХЛ", "NHL", "АХЛ", "AHL", "КХЛ", "ВХЛ", "МХЛ", "АЗИЯ", "ASIA", "ЧЕХИЯ", "ФИНЛЯНДИЯ", "ГЕРМАНИЯ", "ШВЕЙЦАРИЯ", "АВСТРИЯ"]

class HockeyScanner:
    def __init__(self):
        self.url = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "XMLHttpRequest",
            "Referer": "https://www.flashscore.ru/"
        }
        self.sent_cache = {} # Храним ID: (home, away) для отчетов

    def _get_val(self, block, tag):
        try: return block.split(tag)[1].split('¬')[0].strip()
        except: return ""

    async def run(self):
        logger.info("=== v26.2 ЗАПУЩЕН | ОТЧЕТЫ + ГЛУБОКИЙ ПАРСИНГ БРОСКОВ ===")
        async with AsyncSession(impersonate="chrome110") as session:
            while True:
                try:
                    r = await session.get(f"{self.url}?t={int(time.time())}", headers=self.headers, timeout=20)
                    if r.status_code != 200:
                        await asyncio.sleep(20); continue

                    sections = r.text.split('~ZA÷')
                    for sec in sections[1:]:
                        league_raw = sec.split('¬')[0]
                        if not any(lg.upper() in league_raw.upper() for lg in STAT_LEAGUES):
                            continue
                            
                        matches = sec.split('~AA÷')
                        for m_block in matches[1:]:
                            m_id = m_block.split('¬')[0]
                            status = self._get_val(m_block, 'AC÷')
                            home = self._get_val(m_block, 'AE÷')
                            away = self._get_val(m_block, 'AF÷')
                            gh = self._get_val(m_block, 'AG÷')
                            ga = self._get_val(m_block, 'AH÷')

                            # 1. ПРОВЕРКА ЗАНОСОВ (для тех, что уже отправили)
                            if m_id in self.sent_cache:
                                h2 = self._get_val(m_block, 'BC÷')
                                a2 = self._get_val(m_block, 'BD÷')
                                
                                # Если забили во 2-м
                                if (h2.isdigit() and int(h2) > 0) or (a2.isdigit() and int(a2) > 0):
                                    await bot.send_message(CHANNEL_ID, f"✅✅✅ **ЗАНОС!**\n🏒 {home} — {away}\nГол во втором периоде! Есть результат!")
                                    del self.sent_cache[m_id]
                                    continue

                                # Если 2-й период кончился в сухую (статус 13 или 45)
                                if status in ['13', '45']:
                                    if h2 == "0" and a2 == "0":
                                        await bot.send_message(CHANNEL_ID, f"❌ **МИНУС**\n🏒 {home} — {away}\nВторой период завершился 0:0.")
                                    del self.sent_cache[m_id]
                                    continue

                            # 2. ПОИСК НОВЫХ СИГНАЛОВ
                            if status == '46' and m_id not in self.sent_cache:
                                # Проверка, что 2-й период точно еще не начался
                                if self._get_val(m_block, 'BC÷') == "":
                                    curr_total = (int(gh) if gh.isdigit() else 0) + (int(ga) if ga.isdigit() else 0)
                                    
                                    # Фильтр: только 0:0, 1:0 или 0:1
                                    if curr_total <= 1:
                                        # Глубокий поиск бросков
                                        sh = self._get_val(m_block, 'AS÷') or self._get_val(m_block, 'BS÷')
                                        sa = self._get_val(m_block, 'AT÷') or self._get_val(m_block, 'BT÷')
                                        
                                        # Если бросков нет, подождем 15 сек и попробуем еще раз (только для этого матча)
                                        if not sh.isdigit():
                                            await asyncio.sleep(15)
                                            # Запрашиваем данные снова внутри цикла не получится просто, 
                                            # поэтому выводим то что есть или метку
                                            shots_text = f"{sh}:{sa}" if sh.isdigit() else "Загрузка..."
                                        else:
                                            shots_text = f"{sh}:{sa}"

                                        link = f"https://www.flashscore.ru/match/{m_id}/#/match-summary"
                                        text = (
                                            f"🏒 **{home} {gh}:{ga} {away}**\n"
                                            f"🏆 {league_raw}\n\n"
                                            f"📊 Броски (1-й): `{shots_text}`\n"
                                            f"🎯 Ждем гол во 2-м периоде!\n\n"
                                            f"🔗 [ОТКРЫТЬ МАТЧ]({link})"
                                        )
                                        
                                        await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown", disable_web_page_preview=True)
                                        self.sent_cache[m_id] = (home, away)
                                        logger.info(f"✅ ОТПРАВЛЕНО: {home}-{away}")

                    if len(self.sent_cache) > 150: self.sent_cache.clear()
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
                
                await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(HockeyScanner().run())
