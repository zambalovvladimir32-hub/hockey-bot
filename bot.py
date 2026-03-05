import asyncio
import os
import json
import re
import aiohttp
from playwright.async_api import async_playwright

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL") 
DB_MATCHES = "tracked_matches.json"

TRACKED_MATCHES = {}

def save_data():
    with open(DB_MATCHES, "w", encoding="utf-8") as f:
        json.dump(TRACKED_MATCHES, f)

def load_data():
    global TRACKED_MATCHES
    if os.path.exists(DB_MATCHES):
        with open(DB_MATCHES, "r", encoding="utf-8") as f:
            TRACKED_MATCHES = json.load(f)

async def send_tg(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        try: await session.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
        except: pass

async def main():
    print(f"--- 🦾 БОТ V31: ДИАГНОСТИКА + MOBILE MODE ---", flush=True)
    load_data()
    
    async with async_playwright() as p:
        proxy = {"server": PROXY_URL} if PROXY_URL else None
        browser = await p.chromium.launch(headless=True, proxy=proxy, args=['--no-sandbox'])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1"
        )

        # 1. ТЕСТ ПРОКСИ
        test_page = await context.new_page()
        print("🌐 Тестирую прокси...", flush=True)
        try:
            await test_page.goto("https://icanhazip.com", timeout=20000)
            ip = (await test_page.content()).strip()
            print(f"✅ Прокси работает! IP: {ip}", flush=True)
        except Exception as e:
            print(f"❌ ПРОКСИ СДОХ: {e}", flush=True)
        await test_page.close()

        main_page = await context.new_page()
        
        while True:
            try:
                print("\n📡 Загружаю мобильную версию...", flush=True)
                # Пробуем зайти на m.flashscore.com или мобильный юзер-агент
                await main_page.goto("https://www.flashscore.com/hockey/", timeout=60000, wait_until="commit")
                await asyncio.sleep(5) # Ждем прогрузки JS
                
                if await main_page.locator(".event__match").count() == 0:
                    print("⚠️ Матчи не найдены. Возможно, пустая страница или блок.", flush=True)
                    continue

                rows = await main_page.locator(".event__match").all()
                print(f"📊 Нашел матчей: {len(rows)}", flush=True)
                
                for row in rows:
                    stage_el = row.locator(".event__stage")
                    if await stage_el.count() == 0: continue
                    stage = (await stage_el.inner_text()).lower()
                    
                    if "break" not in stage and "перерыв" not in stage: continue
                    
                    m_id = (await row.get_attribute("id") or "").split("_")[-1]
                    if not m_id or m_id in TRACKED_MATCHES: continue

                    home = await row.locator(".event__participant--home").inner_text()
                    away = await row.locator(".event__participant--away").inner_text()
                    
                    # Быстрый сбор статы через переход
                    det = await context.new_page()
                    try:
                        await det.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/0", timeout=40000)
                        await det.wait_for_selector(".stat__row", timeout=15000)
                        
                        content = await det.evaluate("document.body.innerText")
                        # Ищем цифры бросков
                        m_sh = re.search(r"(\d+)[\s\n]+(?:Shots on Goal|Броски в створ)[\s\n]+(\d+)", content, re.I)
                        if m_sh:
                            total_sh = int(m_sh.group(1)) + int(m_sh.group(2))
                            if total_sh >= 13:
                                await send_tg(f"🚨 <b>СИГНАЛ: {home}-{away}</b>\n🎯 Броски: {total_sh}")
                                TRACKED_MATCHES[m_id] = {"home": home, "away": away, "p1_total": 0}
                                save_data()
                    except: pass
                    finally: await det.close()

                await asyncio.sleep(60)
            except Exception as e:
                print(f"⚠️ Ошибка: {e}", flush=True)
                await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
