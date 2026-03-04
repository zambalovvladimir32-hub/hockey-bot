import asyncio
from playwright.async_api import async_playwright

async def debug_flashscore():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        page = await browser.new_page()
        # Идем на вчерашний день через параметр ?d=-1
        print("🌍 Пробую зайти на результаты вчерашнего дня...")
        await page.goto("https://www.flashscore.com/hockey/?d=-1", timeout=60000)
        await page.wait_for_timeout(5000) # Ждем 5 сек
        
        title = await page.title()
        print(f"📄 Заголовок страницы: {title}")
        
        content = await page.content()
        if "event__match" in content:
            print("✅ Матчи найдены! Значит, просто нужно было другое время ожидания.")
        else:
            print("❌ Матчей нет. На странице только HTML-код защиты или пустота.")
            print(f"🔍 Кусок кода: {content[:500]}")
        
        await browser.close()

asyncio.run(debug_flashscore())
