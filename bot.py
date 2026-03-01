import asyncio, os, logging, sys, time
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeyV32.1")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

# Список лиг для мониторинга
LEAGUES = ["НХЛ", "NHL", "АХЛ", "AHL", "КХЛ", "ВХЛ", "МХЛ", "ЧЕХИЯ", "ГЕРМАНИЯ", "ФИНЛЯНДИЯ", "ШВЕЙЦАРИЯ", "ШВЕЦИЯ", "АВСТРИЯ"]

class HockeySniper:
    def __init__(self):
        # Используем основной фид
        self.url_main = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "x-fsign": "SW9D1eZo", # Ключ может требовать обновления
            "x-requested-with": "XMLHttpRequest",
            "Referer": "https://www.flashscore.ru/"
        }
        self.sent_cache = {}

    def _get_val(self, block, tag):
        try: return block.split(tag)[1].split('¬')[0].strip()
        except: return ""

    async def get_stats(self, session, m_id, h_name, a_name):
        """Пытаемся достать данные через мобильные эндпоинты"""
        # Пробуем 3 разных варианта запроса статы
        endpoints = [f"d_st_{m_id}_ru-ru_1", f"d_st_{m_id}_en-gb_1", f"d_su_{m_id}_ru-ru_1"]
        
        for ep in endpoints:
            url = f"https://www.flashscore.ru/x/feed/{ep}"
            try:
                logger.info(f"🔎 Пробую получить стату: {h_name} ({ep})")
                r = await session.get(url, headers=self.headers, timeout=12)
                
                if r.status_code != 200:
                    logger.warning(f"📡 Код {r.status_code} для {ep}")
                    continue
                
                d = r.text
                if "¬" not in d:
                    logger.warning(f"📭 Пустой ответ от {ep}")
                    continue

                st = {"shots": 0, "pen": 0}
                # Парсим "Удары по воротам" или "Броски"
                for tag in ["Удары по воротам", "Вратарь отбивает мяч", "Удары в створ", "SG÷"]:
                    if tag in d:
                        parts = d.split(tag)[1].split("~")[0].split("¬")
                        vals = [p.split("÷")[1] for p in parts if "÷" in p and p.split("÷")[1].isdigit()]
                        if len(vals) >= 2:
                            st["shots"] = int(vals[0]) + int(vals[1])
                            break
                
                # Парсим "ПИМ"
                for tag in ["ПИМ", "Штрафное время", "Штрафы"]:
                    if tag in d:
                        parts = d.split(tag)[1].split("~")[0].split("¬")
                        vals = [p.split("÷")[1] for p in parts if "÷" in p and p.split("÷")[1].isdigit()]
                        if len(vals) >= 2:
                            st["pen"] = int(vals[0]) + int(vals[1])
                            break
                
                if st["shots"] > 0:
                    logger.info(f"✅ ДАННЫЕ ПОЛУЧЕНЫ: Броски={st['shots']}, ПИМ={st['pen']}")
                    return st
            except Exception as e:
                logger.error(f"⚠️ Ошибка на {ep}: {e}")
        return None

    async def run(self):
        logger.info("=== v32.1 MOBILE-PROXY ЗАПУЩЕН ===")
        async with AsyncSession(impersonate="safari_ios_16_0") as session:
            while True:
                try:
                    r = await session.get(f"{self.url_main}?t={int(time.time())}", headers=self.headers, timeout=20)
                    if r.status_code != 200:
                        logger.error(f"❌ Ошибка ленты: {r.status_code}")
                        await asyncio.sleep(30); continue
                    
                    matches_count = len(r.text.split('~AA÷')) - 1
                    logger.info(f"📡 Сердцебиение: вижу {matches_count} матчей.")
                    
                    for sec in r.text.split('~ZA÷')[1:]:
                        league = sec.split('¬')[0]
                        is_target = any(lg.upper() in league.upper() for lg in LEAGUES)
                        
                        for m_block in sec.split('~AA÷')[1:]:
                            m_id = m_block.split('¬')[0]
                            status = self._get_val(m_block, 'AC÷')
                            
                            # Только ПЕРЕРЫВ (46)
                            if status == '46' and is_target:
                                h, a = self._get_val(m_block, 'AE÷'), self._get_val(m_block, 'AF÷')
                                gh, ga = self._get_val(m_block, 'AG÷'), self._get_val(m_block, 'AH÷')
                                
                                if m_id not in self.sent_cache and self._get_val(m_block, 'BC÷') == "":
                                    score = (int(gh) if gh.isdigit() else 0) + (int(ga) if ga.isdigit() else 0)
                                    if score <= 1:
                                        logger.info(f"🎯 Проверка статы для: {h} - {a} (Счет {gh}:{ga})")
                                        stats = await self.get_stats(session, m_id, h, a)
                                        
                                        if stats:
                                            # Твои условия по броскам (11) или штрафам (4)
                                            if stats["shots"] >= 11 or stats["pen"] >= 4:
                                                label = "🔥 GOLD" if stats["shots"] >= 16 else "💎 СИГНАЛ"
                                                text = (
                                                    f"🏒 **{h} {gh}:{ga} {a}**\n🏆 {league}\n\n"
                                                    f"📊 **Статистика (1-й период):**\n"
                                                    f"🎯 Броски/Сэйвы: `{stats['shots']}`\n"
                                                    f"⚖️ ПИМ (Штрафы): `{stats['pen']} мин`"
                                                    f"\n\nРейтинг: **{label}**\n🔗 [МАТЧ](https://www.flashscore.ru/match/{m_id}/#/match-summary)"
                                                )
                                                await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown", disable_web_page_preview=True)
                                                self.sent_cache[m_id] = f"{h}-{a}"
                                                logger.info(f"🚀 СИГНАЛ ОТПРАВЛЕН!")
                                            else:
                                                logger.info(f"📉 Слабая стата для {h}")
                    
                    await asyncio.sleep(40)
                except Exception as e:
                    logger.error(f"Критическая ошибка: {e}")
                    await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(HockeySniper().run())
