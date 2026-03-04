import asyncio
import os
import aiohttp
from playwright.async_api import async_playwright
from datetime import datetime, timedelta

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")

async def send_tg(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        await session.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})

async def check_stats_presence(context, match_id):
    page = await context.new_page()
    try:
        # Прямая ссылка на вкладку статистики
        await page.goto(f"https://www.flashscore.com/match/{match_id}/#/match-summary/match-statistics/0", timeout=45000)
        # Ждем именно блок со статистикой
        await page.wait_for_selector(".stat__row", timeout=10000)
        content = await page.content()
        return "Shots on Goal" in content or "Выстрелы по цели" in content
    except:
        return False
    finally:
        await page.close()

async def main():
    print("--- 🔍 НАЧИНАЮ ПОВТОРНЫЙ АУДИТ (УВЕЛИЧЕННЫЕ ТАЙМАУТЫ) ---", flush=True)
    verified_leagues = set()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...")
        page = await context.new_page()
        
        # Проверяем последние 4 дня
        for i in range(1, 5):
            date_str = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            print(f"📅 Проверка архива за: {date_str}...", flush=True)
            
            try:
                # Ждем полной загрузки страницы
                await page.goto(f"https://www.flashscore.com/hockey/{date_str}/", timeout=60000, wait_until="networkidle")
                
                # Ждем появления списка матчей (увеличил до 30 сек)
                await page.wait_for_selector(".event__match", timeout=30000)
                
                rows = await page.locator(".event__header, .event__match").all()
                current_league = ""
                
                for row in rows:
                    class_name = await row.get_attribute("class")
                    if "event__header" in class_name:
                        title_node = row.locator(".event__title--name")
                        if await title_node.count() > 0:
                            current_league = await title_node.inner_text()
                    elif "event__match" in class_name and current_league and current_league not in verified_leagues:
                        match_id = (await row.get_attribute("id")).split("_")[-1]
                        
                        print(f"   🔎 Проверяю лигу: {current_league}...", flush=True)
                        has_stats = await check_stats_presence(context, match_id)
                        
                        if has_stats:
                            print(f"   ✅ ЕСТЬ СТАТИСТИКА!")
                            verified_leagues.add(current_league)
                        else:
                            print(f"   ❌ Статистики нет.")
                            
            except Exception as e:
                print(f"⚠️ Ошибка на дате {date_str}: {e}")

        await browser.close()

    if verified_leagues:
        sorted_leagues = sorted(list(verified_leagues))
        msg = "📋 <b>ОТЧЕТ ПО АУДИТУ ЛИГ</b>\n\nЭти турниры присылают броски:\n"
        msg += "\n".join([f"• <code>{l}</code>" for l in sorted_leagues])
        
        code_part = "\n\n<b>WHITE_LIST для твоего бота:</b>\n"
        code_part += "<code>WHITE_LIST = [\n    \"" + '",\n    "'.join(sorted_leagues) + "\"\n]</code>"
        
        await send_tg(msg + code_part)
        print("--- ✅ ОТЧЕТ ОТПРАВЛЕН ---")
    else:
        print("❌ Не удалось найти лиги даже с большими таймаутами.")
        await send_tg("⚠️ Аудит завершен, но лиги со статистикой не найдены. Возможно, в эти дни не было крупных турниров.")

if __name__ == "__main__":
    asyncio.run(main())
