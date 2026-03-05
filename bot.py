import asyncio
import os
import json
import re
import aiohttp
from playwright.async_api import async_playwright

# --- КОНФИГ ---
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
        try:
            await session.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
        except: pass

# --- ФУНКЦИЯ УСКОРЕНИЯ (Блокировка картинок/рекламы) ---
async def block_aggressively(route):
    if route.request.resource_type in ["image", "media", "font", "stylesheet"]:
        await route.abort()
    else:
        await route.continue_()

async def main():
    print(f"--- 🦾 БОТ V30: ТУРБО-ЛАЙТ (ПРОКСИ) ---", flush=True)
    load_data()
    
    async with async_playwright() as p:
        proxy_settings = {"server": PROXY_URL} if PROXY_URL else None
        
        browser = await p.chromium.launch(
            headless=True, 
            proxy=proxy_settings,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720}
        )

        # Подключаем блокировщик на весь контекст
        await context.route("**/*", block_aggressively)

        main_page = await context.new_page()
        
        while True:
            try:
                print("\n📡 Обновляю линию...", flush=True)
                # Ждем только DOM, а не всю страницу целиком
                await main_page.goto("https://www.flashscore.com/hockey/", timeout=90000, wait_until="domcontentloaded")
                await main_page.wait_for_selector(".event__match", timeout=30000)
                
                rows = await main_page.locator(".event__header, .event__match").all()
                cur_league = "Неизвестная лига"
                
                for row in rows:
                    cls = await row.get_attribute("class") or ""
                    
                    if "event__header" in cls:
                        try:
                            l_text = await row.inner_text()
                            parts = [p.strip() for p in l_text.split('\n') if p.strip()]
                            if parts: cur_league = " - ".join(parts[:2])
                        except: pass
                        continue
                    
                    if "event__match" in cls:
                        stage_el = row.locator(".event__stage")
                        if await stage_el.count() == 0: continue
                        stage = (await stage_el.inner_text()).lower()
                        
                        if "break" not in stage and "перерыв" not in stage: continue
                        if any(x in stage for x in ["2nd", "3rd", "2-й", "3-й"]): continue
                        
                        m_id = (await row.get_attribute("id") or "").split("_")[-1]
                        if not m_id or m_id in TRACKED_MATCHES: continue

                        sc_h_txt = await row.locator(".event__score--home").inner_text()
                        sc_a_txt = await row.locator(".event__score--away").inner_text()
                        if not sc_h_txt.isdigit() or not sc_a_txt.isdigit() or (int(sc_h_txt) + int(sc_a_txt)) > 1: continue

                        home = await row.locator(".event__participant--home").inner_text()
                        away = await row.locator(".event__participant--away").inner_text()
                        
                        print(f"   🎯 КАНДИДАТ: {home} - {away}", flush=True)
                        
                        det = await context.new_page()
                        try:
                            # Статистика
                            await det.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/0", timeout=45000, wait_until="domcontentloaded")
                            await det.wait_for_selector(".stat__row", timeout=20000)

                            content = await det.evaluate("document.body.innerText")
                            total_sh, total_wh, total_pim = None, 0, 0
                            
                            m_sh = re.search(r"(\d+)[\s\n]+(?:Shots on Goal|Броски в створ|Střely na branku)[\s\n]+(\d+)", content, re.I)
                            if m_sh: total_sh = int(m_sh.group(1)) + int(m_sh.group(2))
                            
                            m_wh = re.search(r"(\d+)[\s\n]+(?:Penalties|Удаления|Vyloučení)[\s\n]+(\d+)", content, re.I)
                            if m_wh: total_wh = int(m_wh.group(1)) + int(m_wh.group(2))
                            
                            m_pim = re.search(r"(\d+)[\s\n]+(?:PIM|Penalty Minutes|Штрафное время)[\s\n]+(\d+)", content, re.I)
                            if m_pim: total_pim = int(m_pim.group(1)) + int(m_pim.group(2))

                            if total_sh is not None and total_sh >= 13 and total_pim >= 2 and total_wh >= 1:
                                msg = (f"🚨 <b>СИГНАЛ: ПЕРЕРЫВ P1</b>\n🏆 {cur_league}\n🤝 {home} — {away}\n"
                                       f"🎯 Броски: {total_sh} | ❌ Удаления: {total_wh} | ⏳ Штраф: {total_pim} мин")
                                await send_tg(msg)
                                TRACKED_MATCHES[m_id] = {"home": home, "away": away, "p1_total": int(sc_h_txt) + int(sc_a_txt)}
                                save_data()
                                print("      ✅ СИГНАЛ УШЕЛ!", flush=True)
                        except Exception as e: print(f"      ⚠️ Детали: {e}", flush=True)
                        finally: await det.close()
                
                print(f"💤 Сплю 60 сек...", flush=True)
                await asyncio.sleep(60)
            except Exception as e:
                print(f"⚠️ Ошибка: {e}", flush=True)
                await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
