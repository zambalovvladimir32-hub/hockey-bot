import asyncio
import os
import json
import re
from playwright.async_api import async_playwright

# --- КОНФИГ (Берём строго из переменных окружения) ---
PROXY_URL = os.getenv("PROXY_URL") 
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
DB_MATCHES = "tracked_matches.json"

TRACKED_MATCHES = {}

def save_data():
    with open(DB_MATCHES, "w", encoding="utf-8") as f:
        json.dump(TRACKED_MATCHES, f)

def load_data():
    global TRACKED_MATCHES
    if os.path.exists(DB_MATCHES) and os.path.getsize(DB_MATCHES) > 0:
        with open(DB_MATCHES, "r", encoding="utf-8") as f:
            try:
                TRACKED_MATCHES = json.load(f)
            except: TRACKED_MATCHES = {}

async def send_tg(text):
    if not TOKEN or not CHAT_ID: return
    import aiohttp
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        try: 
            await session.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
        except: pass

async def main():
    print(f"--- 🦾 БОТ V48: БЕЗОПАСНАЯ СБОРКА ---", flush=True)
    load_data()
    
    if not PROXY_URL:
        print("❌ ОШИБКА: Переменная PROXY_URL не найдена в настройках!", flush=True)
        return

    async with async_playwright() as p:
        # Используем прокси из переменных
        proxy_cfg = {"server": PROXY_URL}
        
        browser = await p.chromium.launch(headless=True, proxy=proxy_cfg, args=['--no-sandbox'])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        page = await context.new_page()
        # Отключаем картинки для экономии трафика и скорости
        await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "font"] else route.continue_())

        while True:
            try:
                print(f"\n📡 Сканирую Flashscore.ru (Live)...", flush=True)
                
                # Заходим в раздел хоккея
                await page.goto("https://www.flashscore.ru/hockey/", timeout=45000, wait_until="domcontentloaded")
                await asyncio.sleep(7) 

                rows = await page.locator(".event__match").all()
                print(f"📊 Матчей в лайве: {len(rows)}", flush=True)
                
                for row in rows:
                    try:
                        # Фильтр: только ПЕРЕРЫВ
                        stage_text = (await row.locator(".event__stage").inner_text()).lower()
                        if "перерыв" not in stage_text and "break" not in stage_text: continue
                        if any(x in stage_text for x in ["2-й", "3-й", "2nd", "3rd"]): continue

                        m_id = (await row.get_attribute("id")).split("_")[-1]
                        if m_id in TRACKED_MATCHES: continue

                        # Фильтр: СЧЕТ (0:0, 1:0, 0:1)
                        sc_h = await row.locator(".event__score--home").inner_text()
                        sc_a = await row.locator(".event__score--away").inner_text()
                        
                        if not (sc_h.isdigit() and sc_a.isdigit()): continue
                        if (int(sc_h) + int(sc_a)) > 1: continue

                        home = await row.locator(".event__participant--home").inner_text()
                        away = await row.locator(".event__participant--away").inner_text()
                        
                        print(f"   🎯 Найден подходящий матч: {home} - {away}. Проверяю статку...", flush=True)

                        # Переходим в статистику
                        det = await context.new_page()
                        try:
                            await det.goto(f"https://www.flashscore.ru/match/{m_id}/#/match-summary/match-statistics/0", timeout=30000)
                            await det.wait_for_selector(".stat__row", timeout=12000)
                            
                            content = await det.evaluate("document.body.innerText")
                            
                            # Поиск данных через Regex (поддержка разных языков)
                            sh = re.search(r"(\d+)[\s\n]+(?:Броски в створ|Shots on Goal|Střely na branku)[\s\n]+(\d+)", content, re.I)
                            wh = re.search(r"(\d+)[\s\n]+(?:Удаления|Penalties|Vyloučení)[\s\n]+(\d+)", content, re.I)
                            pim = re.search(r"(\d+)[\s\n]+(?:Штрафное время|PIM|Trestné minuty)[\s\n]+(\d+)", content, re.I)

                            if sh:
                                t_sh = int(sh.group(1)) + int(sh.group(2))
                                t_wh = int(wh.group(1)) + int(wh.group(2)) if wh else 0
                                t_pim = int(pim.group(1)) + int(pim.group(2)) if pim else 0
                                
                                print(f"      📊 Итог: Бр={t_sh}, Свист={t_wh}, Штр={t_pim}", flush=True)

                                if t_sh >= 13 and t_pim >= 2 and t_wh >= 1:
                                    msg = (f"🚨 <b>СИГНАЛ: ПЕРЕРЫВ P1</b>\n"
                                           f"🤝 {home} — {away} ({sc_h}:{sc_a})\n"
                                           f"🎯 Броски: {t_sh} | ❌ Удаления: {t_wh} | ⏳ Штраф: {t_pim} мин")
                                    await send_tg(msg)
                                    TRACKED_MATCHES[m_id] = {"home": home, "away": away}
                                    save_data()
                            else:
                                print("      ❌ Статистика еще пуста.", flush=True)
                        except: pass
                        finally: await det.close()

                    except: continue

                await asyncio.sleep(60)
            except Exception as e:
                print(f"⚠️ Ошибка цикла: {e}", flush=True)
                await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(main())
