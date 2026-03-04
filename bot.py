import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, timedelta
import os
import aiohttp

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")

async def send_tg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        await session.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})

async def audit_leagues():
    print("--- 🔍 НАЧИНАЮ АУДИТ АРХИВА (3-4 ДНЯ) ---", flush=True)
    
    verified_leagues = set()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0...")
        page = await context.new_page()
        
        # Проверяем последние 4 дня
        for i in range(1, 5):
            date_str = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            url = f"https://www.flashscore.com/hockey/{date_str}/"
            print(f"📅 Проверяю дату: {date_str}")
            
            try:
                await page.goto(url, timeout=60000)
                await page.wait_for_selector(".event__match", timeout=10000)
                
                # Собираем лиги и их первые матчи
                elements = await page.locator(".event__header, .event__match").all()
                current_league = ""
                
                for el in elements:
                    classes = await el.get_attribute("class")
                    if "event__header" in classes:
                        current_league = await el.locator(".event__title--name").inner_text()
                    elif "event__match" in classes and current_league not in verified_leagues:
                        match_id = (await el.get_attribute("id")).split("_")[-1]
                        
                        # Проверяем, есть ли стата в этом матче
                        stat_page = await context.new_page()
                        try:
                            await stat_page.goto(f"https://www.flashscore.com/match/{match_id}/#/match-summary/match-statistics/0", timeout=20000)
                            await stat_page.wait_for_timeout(2000)
                            content = await stat_page.content()
                            
                            # Если нашли "Shots on Goal" или "Выстрелы по цели"
                            if "Shots on Goal" in content or "Выстрелы по цели" in content:
                                print(f"  ✅ Лига одобрена: {current_league}")
                                verified_leagues.add(current_league)
                        except: pass
                        finally: await stat_page.close()
                        
            except Exception as e:
                print(f"Ошибка даты {date_str}: {e}")

        await browser.close()

    # Формируем список для ТГ
    if verified_leagues:
        leagues_list = "\n".join([f"• {l}" for l in sorted(verified_leagues)])
        # Формируем Python-массив для копирования
        python_array = 'WHITE_LIST = [\n    "' + '",\n    "'.join(sorted(verified_leagues)) + '"\n]'
        
        await send_tg(f"📋 <b>Белый список лиг (со статой за 4 дня):</b>\n\n{leagues_list}")
        await send_tg(f"<code>{python_array}</code>")
        print("--- ✅ АУДИТ ЗАВЕРШЕН, СПИСОК В ТЕЛЕГРАМЕ ---")
    else:
        print("❌ Не удалось найти лиги со статистикой.")

if __name__ == "__main__":
    asyncio.run(audit_leagues())
