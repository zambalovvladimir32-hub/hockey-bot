import asyncio, os, logging, sys
from aiogram import Bot
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeyV35.0")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL") # Формат: http://user:pass@ip:port
bot = Bot(token=TOKEN)

class HockeySniper:
    def __init__(self):
        self.main_page = "https://www.flashscore.ru/"
        self.sent_cache = {}

    async def get_stats_via_browser(self, browser_context, m_id):
        page = await browser_context.new_page()
        try:
            # Заходим прямо на страницу статистики матча
            url = f"https://www.flashscore.ru/match/{m_id}/#/match-summary/match-statistics/0"
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3) # Даем время скриптам отрисовать таблицу

            # Ищем броски и штрафы прямо в HTML коде страницы
            content = await page.content()
            st = {"shots": 0, "pen": 0}

            # Логика поиска в DOM-структуре
            if "Броски" in content or "Удары по воротам" in content:
                # Извлекаем цифры через селекторы (типичные для Flashscore)
                rows = await page.query_selector_all(".stat__row")
                for row in rows:
                    text = await row.inner_text()
                    if "Броски" in text or "Удары" in text:
                        vals = await row.query_selector_all(".stat__value")
                        st["shots"] = int(await vals[0].inner_text()) + int(await vals[1].inner_text())
                    if "Штраф" in text or "ПИМ" in text:
                        vals = await row.query_selector_all(".stat__value")
                        st["pen"] = int(await vals[0].inner_text()) + int(await vals[1].inner_text())
            
            await page.close()
            return st if (st["shots"] > 0 or st["pen"] > 0) else None
        except Exception as e:
            logger.error(f"Ошибка браузера на {m_id}: {e}")
            await page.close()
            return None

    async def run(self):
        logger.info("=== v35.0 BROWSER-ENGINE ЗАПУЩЕН ===")
        
        async with async_playwright() as p:
            # Запуск браузера с твоим резидентским прокси
            proxy_config = None
            if PROXY_URL:
                p_parts = PROXY_URL.replace("http://", "").split("@")
                auth = p_parts[0].split(":")
                server = p_parts[1]
                proxy_config = {"server": f"http://{server}", "username": auth[0], "password": auth[1]}

            browser = await p.chromium.launch(headless=True) # headles=True для Railway
            context = await browser.new_context(proxy=proxy_config, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

            while True:
                try:
                    # Мониторинг главной страницы через браузер
                    page = await context.new_page()
                    await page.goto(self.main_page, wait_until="networkidle")
                    
                    # Ищем все матчи в перерыве (фильтр по тексту "Перерыв")
                    matches = await page.query_selector_all(".event__match--scheduled") # Уточнить селектор по факту
                    # Это упрощенная логика, для полной нужно парсить список матчей
                    
                    # Для теста: если мы знаем m_id из логов (например, Филлах)
                    test_ids = ["fba2A8Ym"] # Пример ID матча Филлах из твоих логов
                    
                    for m_id in test_ids:
                        if m_id in self.sent_cache: continue
                        
                        logger.info(f"🌐 Браузерный анализ матча {m_id}...")
                        stats = await self.get_stats_via_browser(context, m_id)
                        
                        if stats:
                            logger.info(f"📊 ДАННЫЕ ПОЛУЧЕНЫ: {stats}")
                            if stats["shots"] >= 11 or stats["pen"] >= 4:
                                await bot.send_message(CHANNEL_ID, f"✅ СИГНАЛ (Browser): Броски {stats['shots']}, ПИМ {stats['pen']}")
                                self.sent_cache[m_id] = True
                    
                    await page.close()
                    await asyncio.sleep(60)
                except Exception as e:
                    logger.error(f"Ошибка цикла: {e}")
                    await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(HockeySniper().run())
