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
        try: await session.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
        except: pass

async def main():
    print(f"--- 🦾 БОТ V37: ПРОВЕРКА НАСТРОЕК ---", flush=True)
    
    # --- БЛОК ДИАГНОСТИКИ ---
    print(f"🛠 ПРОВЕРКА ПЕРЕМЕННЫХ:", flush=True)
    print(f"  - TELEGRAM_TOKEN: {'✅ Ок' if TOKEN else '❌ ПУСТО'}", flush=True)
    print(f"  - CHANNEL_ID: {'✅ Ок' if CHAT_ID else '❌ ПУСТО'}", flush=True)
    if PROXY_URL:
        # Маскируем пароль для безопасности в логах
        masked_proxy = re.sub(r":.*@", ":******@", PROXY_URL)
        print(f"  - PROXY_URL: ✅ Вижу ({masked_proxy})", flush=True)
    else:
        print(f"  - PROXY_URL: ❌ ПУСТО (Бот работает без прокси!)", flush=True)
    
    load_data()
    
    async with async_playwright() as p:
        proxy_cfg = {"server": PROXY_URL} if PROXY_URL else None
        
        browser = await p.chromium.launch(headless=True, proxy=proxy_cfg, args=['--no-sandbox'])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"
        )

        main_page = await context.new_page()
        # Отключаем всё тяжелое
        await main_page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "font", "media"] else route.continue_())

        while True:
            try:
                print("\n📡 Скребу линию...", flush=True)
                # Пытаемся зайти на мобильный домен, он часто быстрее
                try:
                    await main_page.goto("https://www.flashscore.com/hockey/", timeout=45000, wait_until="commit")
                    await asyncio.sleep(8)
                except Exception as e:
                    print(f"⚠️ Ошибка загрузки: {e}. Пробую еще раз...", flush=True)
                    continue

                rows = await main_page.locator(".event__match").all()
                print(f"📊 Матчей нашел: {len(rows)}", flush=True)
                
                for row in rows:
                    try:
                        stage = (await row.locator(".event__stage").inner_text()).lower()
                        if "break" not in stage and "перерыв" not in stage: continue
                        if any(x in stage for x in ["2nd", "3rd", "2-й", "3-й"]): continue
                        
                        m_id = (await row.get_attribute("id")).split("_")[-1]
                        if m_id in TRACKED_MATCHES: continue

                        home = await row.locator(".event__participant--home").inner_text()
                        away = await row.locator(".event__participant--away").inner_text()
                        
                        print(f"   🎯 Проверяю: {home} - {away}", flush=True)
                        
                        det = await context.new_page()
                        try:
                            # Парсим статку (строго по тексту, как на скринах)
                            await det.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/0", timeout=30000, wait_until="commit")
                            await asyncio.sleep(5)
                            
                            full_text = await det.evaluate("document.body.innerText")
                            
                            # Ищем броски, штрафы и удаления
                            sh = re.search(r"(\d+)[\s\n]+(?:Shots on Goal|Střely na branku|Броски в створ)[\s\n]+(\d+)", full_text, re.I)
                            wh = re.search(r"(\d+)[\s\n]+(?:Penalties|Vyloučení|Удаления)[\s\n]+(\d+)", full_text, re.I)
                            pim = re.search(r"(\d+)[\s\n]+(?:PIM|Trestné minuty|Штрафное время)[\s\n]+(\d+)", full_text, re.I)

                            if sh:
                                total_sh = int(sh.group(1)) + int(sh.group(2))
                                total_wh = int(wh.group(1)) + int(wh.group(2)) if wh else 0
                                total_pim = int(pim.group(1)) + int(pim.group(2)) if pim else 0
                                
                                print(f"      📈 Бр: {total_sh} | Свист: {total_wh} | Штр: {total_pim}", flush=True)

                                if total_sh >= 13 and total_pim >= 2 and total_wh >= 1:
                                    msg = (f"🚨 <b>СИГНАЛ: ПЕРЕРЫВ P1</b>\n"
                                           f"🤝 {home} — {away}\n"
                                           f"🎯 Броски: {total_sh} | ❌ Удаления: {total_wh} | ⏳ Штраф: {total_pim} мин")
                                    await send_tg(msg)
                                    TRACKED_MATCHES[m_id] = {"home": home, "away": away, "p1_total": 0}
                                    save_data()
                            else:
                                print("      ❌ Стата не прогрузилась.", flush=True)
                        except: pass
                        finally: await det.close()
                    except: continue

                await asyncio.sleep(60)
            except Exception as e:
                print(f"⚠️ Ошибка: {e}", flush=True)
                await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
