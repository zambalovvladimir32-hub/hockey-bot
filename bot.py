import asyncio, os, logging, sys, time
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeyDebug")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

LEAGUES = ["НХЛ", "NHL", "АХЛ", "AHL", "КХЛ", "ВХЛ", "МХЛ", "ЧЕХИЯ", "ГЕРМАНИЯ", "ФИНЛЯНДИЯ", "ШВЕЙЦАРИЯ", "ШВЕЦИЯ", "АВСТРИЯ"]

class HockeySniper:
    def __init__(self):
        self.url_main = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {"User-Agent": "Mozilla/5.0", "x-fsign": "SW9D1eZo", "x-requested-with": "XMLHttpRequest", "Referer": "https://www.flashscore.ru/"}
        self.sent_cache = {}

    def _get_val(self, block, tag):
        try: return block.split(tag)[1].split('¬')[0].strip()
        except: return ""

    async def get_stats(self, session, m_id, home, away):
        st = {"shots": 0, "attacks": 0, "pen": 0}
        has_stats = False
        url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1"
        
        logger.info(f"⏳ Запрашиваю стату для: {home} - {away} ({url})")
        
        try:
            r = await session.get(url, headers=self.headers, timeout=10)
            logger.info(f"📡 Статус ответа сайта: {r.status_code}")
            
            if r.status_code != 200:
                logger.error(f"❌ ОШИБКА: Сайт вернул код {r.status_code}. Нас заблокировали?")
                return None
                
            d = r.text
            # Печатаем первые 100 символов ответа, чтобы понять, это стата или капча Cloudflare
            logger.info(f"📦 Кусок полученных данных: {d[:100]}...")
            
            # 1. Броски (добавил "Удары по воротам" из твоего видео)
            for tag in ["Вратарь отбивает мяч", "Удары в створ", "Удары по воротам", "SG÷"]:
                if tag in d:
                    v = [x.split("÷")[1] for x in d.split(tag)[1].split("~")[0].split("¬") if "÷" in x and x.split("÷")[1].isdigit()]
                    if len(v) >= 2:
                        st["shots"] = int(v[0]) + int(v[1])
                        has_stats = True
                        logger.info(f"✅ Нашел броски ({tag}): {st['shots']}")
                        break

            # 2. Атаки
            if "Опасные атаки" in d:
                v = [x.split("÷")[1] for x in d.split("Опасные атаки")[1].split("~")[0].split("¬") if "÷" in x and x.split("÷")[1].isdigit()]
                if len(v) >= 2:
                    st["attacks"] = int(v[0]) + int(v[1])
                    has_stats = True
                    logger.info(f"✅ Нашел атаки: {st['attacks']}")

            # 3. Штрафы (из видео)
            for tag in ["ПИМ", "Штрафы", "Штрафное время"]:
                if tag in d:
                    v = [x.split("÷")[1] for x in d.split(tag)[1].split("~")[0].split("¬") if "÷" in x and x.split("÷")[1].isdigit()]
                    if len(v) >= 2: 
                        st["pen"] = int(v[0]) + int(v[1])
                        logger.info(f"✅ Нашел штрафы ({tag}): {st['pen']}")
                        break

        except Exception as e: 
            logger.error(f"❌ Сбой при парсинге статы: {e}")
            
        return st if has_stats else None

    async def run(self):
        logger.info("=== v31.3 DEBUG ЗАПУЩЕН | Ищем перерывы и читаем логи ===")
        async with AsyncSession(impersonate="chrome110") as session:
            while True:
                try:
                    r = await session.get(f"{self.url_main}?t={int(time.time())}", headers=self.headers, timeout=20)
                    if r.status_code != 200: 
                        logger.warning(f"⚠️ Главная страница не отвечает: {r.status_code}")
                        continue
                        
                    for sec in r.text.split('~ZA÷')[1:]:
                        league = sec.split('¬')[0]
                        if not any(lg.upper() in league.upper() for lg in LEAGUES): continue
                        
                        for m_block in sec.split('~AA÷')[1:]:
                            m_id = m_block.split('¬')[0]
                            status = self._get_val(m_block, 'AC÷')
                            gh, ga = self._get_val(m_block, 'AG÷'), self._get_val(m_block, 'AH÷')
                            home, away = self._get_val(m_block, 'AE÷'), self._get_val(m_block, 'AF÷')

                            # Отчеты
                            if m_id in self.sent_cache:
                                h2, a2 = self._get_val(m_block, 'BC÷'), self._get_val(m_block, 'BD÷')
                                if (h2.isdigit() and int(h2) > 0) or (a2.isdigit() and int(a2) > 0):
                                    await bot.send_message(CHANNEL_ID, f"✅ **ЗАНОС!**\n{self.sent_cache[m_id]}\nГол во втором!")
                                    del self.sent_cache[m_id]
                                elif status in ['13', '45']:
                                    await bot.send_message(CHANNEL_ID, f"❌ **МИНУС**\n{self.sent_cache[m_id]}\nВторой период 0:0.")
                                    del self.sent_cache[m_id]
                                continue

                            # ПЕРЕРЫВ - ЛОГИРУЕМ КАЖДЫЙ ШАГ
                            if status == '46' and m_id not in self.sent_cache:
                                if self._get_val(m_block, 'BC÷') == "":
                                    score = (int(gh) if gh.isdigit() else 0) + (int(ga) if ga.isdigit() else 0)
                                    
                                    # Нашли матч по счету
                                    if score <= 1:
                                        logger.info(f"🎯 Пойман ПЕРЕРЫВ с нужным счетом: {home} {gh}:{ga} {away}")
                                        
                                        st = await self.get_stats(session, m_id, home, away)
                                        
                                        if st is None:
                                            logger.info(f"🚫 Пропуск {home}-{away}: нет статы или ошибка парсинга.")
                                            continue
                                            
                                        logger.info(f"🔥 Итоговая стата собрана: {st}")
                                        
                                        if st["shots"] >= 11 or st["attacks"] >= 30 or st["pen"] >= 4:
                                            label = "🔥 GOLD" if (st["shots"] >= 15 and st["pen"] >= 4) else "💎 СИГНАЛ"
                                            text = (
                                                f"🏒 **{home} {gh}:{ga} {away}**\n🏆 {league}\n\n"
                                                f"📊 **Статистика (1-й период):**\n"
                                                f"🎯 Броски: `{st['shots']}`\n"
                                                f"🚀 Оп. атаки: `{st['attacks'] if st['attacks'] > 0 else '?'}`\n"
                                                f"⚖️ Штрафы: `{st['pen']} мин`\n\n"
                                                f"Рейтинг: **{label}**\n🔗 [МАТЧ](https://www.flashscore.ru/match/{m_id}/#/match-summary)"
                                            )
                                            await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown", disable_web_page_preview=True)
                                            self.sent_cache[m_id] = f"{home} — {away}"
                                            logger.info(f"🚀 СИГНАЛ ОТПРАВЛЕН В КАНАЛ: {home} - {away}")
                                        else:
                                            logger.info(f"📉 Стата слабая (бросков: {st['shots']}, штрафов: {st['pen']}). Не шлем.")

                    # Очистка кэша
                    if len(self.sent_cache) > 200: self.sent_cache.clear()
                except Exception as e: logger.error(f"Глобальная ошибка в цикле: {e}")
                await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(HockeySniper().run())
