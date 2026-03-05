import asyncio
import os
import json
import re
from playwright.async_api import async_playwright

# --- КОНФИГ ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
DB_MATCHES = "tracked_matches.json"

TRACKED_MATCHES = {}

def save_data():
    with open(DB_MATCHES, "w", encoding="utf-8") as f:
        json.dump(TRACKED_MATCHES, f)

def load_data():
    global TRACKED_MATCHES
    if os.path.exists(DB_MATCHES):
        with open(DB_MATCHES, "r", encoding="utf-8") as f:
            try: TRACKED_MATCHES = json.load(f)
            except: TRACKED_MATCHES = {}

async def send_tg(text):
    if not TOKEN or not CHAT_ID: return
    import aiohttp
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        try: await session.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
        except: pass

async def main():
    print(f"--- 🦾 БОТ V51: ПРЯМОЕ ПОДКЛЮЧЕНИЕ (БЕЗ ПРОКСИ) ---", flush=True)
    load_data()
    
    async with async_playwright() as p:
        # ЗАПУСК БЕЗ ПРОКСИ
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720}
        )

        page = await context.new_page()
        # Блокируем мусор
        await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "font", "media"] else route.continue_())

        while True:
            try:
                print(f"\n📡 Прямой запрос к Flashscore.com...", flush=True)
                
                # Заходим сразу на LIVE-хоккей
                await page.goto("https://www.flashscore.com/hockey/?s=2", timeout=30000, wait_until="commit")
                await asyncio.sleep(8) 

                title = await page.title()
                print(f"📄 Заголовок: {title}", flush=True)

                # Проверка на бан
                content = await page.evaluate("document.body.innerText")
                if "Access Denied" in content or "Cloudflare" in content or "Verify" in content:
                    print("❌ БАН: Railway IP заблокирован. Без прокси тут не пройти.", flush=True)
                    await asyncio.sleep(60)
                    continue

                rows = await page.locator(".event__match").all()
                print(f"📊 Нашел матчей: {len(rows)}", flush=True)
                
                for row in rows:
                    try:
                        text = (await row.inner_text()).lower()
                        if "break" not in text and "перерыв" not in text: continue
                        if any(x in text for x in ["2nd", "3rd", "2-й", "3-й"]): continue

                        m_id = (await row.get_attribute("id")).split("_")[-1]
                        if m_id in TRACKED_MATCHES: continue

                        # Проверяем счет
                        scores = await row.locator(".event__score").all_inner_texts()
                        if len(scores) >= 2:
                            sc_sum = int(scores[0]) + int(scores[1])
                            if sc_sum > 1: continue
                        else: continue

                        home = await row.locator(".event__participant--home").inner_text()
                        away = await row.locator(".event__participant--away").inner_text()

                        print(f"   🎯 КАНДИДАТ: {home} - {away}. Собираю статику...", flush=True)

                        det = await context.new_page()
                        try:
                            await det.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/0", timeout=20000)
                            await asyncio.sleep(5)
                            
                            st_text = await det.evaluate("document.body.innerText")
                            
                            # Поиск статы
                            sh = re.search(r"(\d+)[\s\n]+(?:Shots on Goal|Броски в створ)[\s\n]+(\d+)", st_text, re.I)
                            if sh:
                                t_sh = int(sh.group(1)) + int(sh.group(2))
                                print(f"      📈 Броски: {t_sh}", flush=True)
                                
                                if t_sh >= 13:
                                    # Вытягиваем удаления и штраф
                                    wh = re.search(r"(\d+)[\s\n]+(?:Penalties|Удаления)[\s\n]+(\d+)", st_text, re.I)
                                    pim = re.search(r"(\d+)[\s\n]+(?:PIM|Штраф)[\s\n]+(\d+)", st_text, re.I)
                                    
                                    t_wh = (int(wh.group(1)) + int(wh.group(2))) if wh else 0
                                    t_pim = (int(pim.group(1)) + int(pim.group(2))) if pim else 0

                                    if t_pim >= 2 and t_wh >= 1:
                                        msg = (f"🚨 <b>СИГНАЛ P1</b>\n"
                                               f"🤝 {home} — {away}\n"
                                               f"🎯 Броски: {t_sh} | ❌ Удаления: {t_wh}")
                                        await send_tg(msg)
                                        TRACKED_MATCHES[m_id] = True
                                        save_data()
                        except: pass
                        finally: await det.close()

                    except: continue

                await asyncio.sleep(60)
            except Exception as e:
                print(f"⚠️ Ошибка: {e}", flush=True)
                await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())
