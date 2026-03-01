import asyncio, os, logging, sys
from aiogram import Bot
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeyV35.1")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL") # Твой Asocks ISP
bot = Bot(token=TOKEN)

async def get_stats(context, m_id):
    page = await context.new_page()
    try:
        # Прямая ссылка на вкладку статистики
        url = f"https://www.flashscore.ru/match/{m_id}/#/match-summary/match-statistics/0"
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5) # Ждем прогрузки JS-таблиц

        content = await page.content()
        st = {"shots": 0, "pen": 0}
        
        # Парсим DOM
        rows = await page.query_selector_all(".stat__row")
        for row in rows:
            text = await row.inner_text()
            if "Броски" in text or "Удары" in text:
                vals = await row.query_selector_all(".stat__value")
                st["shots"] = int(await vals[0].inner_text()) + int(await vals[1].inner_text())
            if "ПИМ" in text or "Штраф" in text:
                vals = await row.query_selector_all(".stat__value")
                st["pen"] = int(await vals[0].inner_text()) + int(await vals[1].inner_text())
        
        await page.close()
        return st if st["shots"] > 0 else None
    except Exception as e:
        logger.error(f"Ошибка на {m_id}: {e}")
        await page.close()
        return None

async def main():
    logger.info("=== v35.1 STARTING BROWSER ENGINE ===")
    async with async_playwright() as p:
        # Настройка прокси для браузера
        auth_data, server_data = PROXY_URL.replace("http://", "").split("@")
        user, password = auth_data.split(":")
        
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            proxy={"server": f"http://{server_data}", "username": user, "password": password},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        while True:
            try:
                # Здесь должна быть логика получения списка ID матчей (m_id)
                # Для теста используем m_id из твоих прошлых логов (например, Филлах)
                test_ids = ["fba2A8Ym"] 
                
                for m_id in test_ids:
                    logger.info(f"🌐 Браузер заходит в матч {m_id}...")
                    res = await get_stats(context, m_id)
                    if res:
                        logger.info(f"📊 УСПЕХ! Броски: {res['shots']}, ПИМ: {res['pen']}")
                        if res["shots"] >= 11:
                            await bot.send_message(CHANNEL_ID, f"🏒 Броски: {res['shots']}")
                
                await asyncio.sleep(120)
            except Exception as e:
                logger.error(f"Global error: {e}")
                await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
