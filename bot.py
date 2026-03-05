import asyncio
import os
import json
import re
import aiohttp
from playwright.async_api import async_playwright

# --- КОНФИГ ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL") # Формат: http://user:pass@ip:port
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
        except Exception as e: print(f"ТГ ошибка: {e}", flush=True)

# ПРОВЕРКА РЕЗУЛЬТАТОВ (ОТЧЕТЫ)
async def check_results(context):
    to_delete = []
    for m_id, data in TRACKED_MATCHES.items():
        page = await context.new_page()
        try:
            await page.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary", timeout=30000)
            status_el = page.locator(".detailScore__status")
            if await status_el.count() == 0: continue
            status = await status_el.inner_text()
            
            if any(x in status for x in ["Break", "3rd", "3-й", "Finished", "Перерыв", "Завершен"]):
                scores = await page.locator(".detailScore__wrapper").inner_text()
                nums = re.findall(r"\d+", scores)
                if len(nums) >= 2:
                    current_total = int(nums[0]) + int(nums[1])
                    if current_total > data['p1_total']:
                        msg = f"✅ <b>ГОЛ ПОЙМАН!</b>\n🤝 {data['home']} — {data['away']}\nСтавка зашла! 🚀"
                    else:
                        msg = f"❌ <b>БЕЗ ГОЛОВ</b>\n🤝 {data['home']} — {data['away']}\n2-й период всухую."
                    await send_tg(msg)
                    to_delete.append(m_id)
        except Exception: pass
        finally: await page.close()
    
    for m_id in to_delete: del TRACKED_MATCHES[m_id]
    if to_delete: save_data()

async def main():
    print(f"--- 🦾 БОТ V28: FINAL PROXY EDITION ---", flush=True)
    load_data()
    
    async with async_playwright() as p:
        proxy_settings = {"server": PROXY_URL} if PROXY_URL else None
        
        browser = await p.chromium.launch(
            headless=True, 
            proxy=proxy_settings,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        # Скрываем автоматизацию
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        main_page = await context.new_page()
        
        while True:
            try:
                if TRACKED_MATCHES: 
                    await check_results(context)

                print("\n📡 Обновляю линию...", flush=True)
                await main_page.goto("https://www.flashscore.com/hockey/", timeout=60000)
                await main_page.wait_for_selector(".event__match", timeout=30000)
                
                rows = await main_page.locator(".event__header, .event__match").all()
                cur_league = "Неизвестная лига"
                
                for row in rows:
                    cls = await row.get_attribute("class") or ""
                    
                    if "event__header" in cls:
                        try:
                            l_text = await row.inner_text()
                            parts = [p.strip() for p in l_text.split('\n') if p.strip() and p.strip() != "New window"]
                            if parts: cur_league = " - ".join(parts[:2])
                        except: pass
                        continue
                    
                    if "event__match" in cls:
                        stage_loc = row.locator(".event__stage")
                        if await stage_loc.count() == 0: continue
                        stage = (await stage_loc.inner_text()).lower()
                        
                        if "break" not in stage and "перерыв" not in stage: continue
                        if any(x in stage for x in ["2nd", "3rd", "2-й", "3-й"]): continue
                        
                        m_id = (await row.get_attribute("id") or "").split("_")[-1]
                        if not m_id or m_id in TRACKED_MATCHES: continue

                        sc_h_txt = await row.locator(".event__score--home").inner_text()
                        sc_a_txt = await row.locator(".event__score--away").inner_text()
                        if not sc_h_txt.isdigit() or not sc_a_txt.isdigit(): continue
                        
                        sc_h, sc_a = int(sc_h_txt), int(sc_a_txt)
                        if (sc_h + sc_a) > 1: continue

                        home = await row.locator(".event__participant--home").inner_text()
                        away = await row.locator(".event__participant--away").inner_text()
                        
                        print(f"   🔍 КАНДИДАТ: {home} - {away} ({sc_h}:{sc_a} | {cur_league})", flush=True)
                        
                        det = await context.new_page()
                        try:
                            # 1. Проверка на 1-й период (через ленту событий)
                            await det.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary", timeout=30000)
                            await det.wait_for_selector(".smv__periodHeader", timeout=10000)
                            headers_count = await det.locator(".smv__periodHeader").count()
                            if headers_count > 1:
                                print("      ❌ Скип: Уже начался 2-й период.", flush=True)
                                continue

                            # 2. Сбор статистики
                            await det.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/0", timeout=30000)
                            try:
                                # Ждем таблицу
                                await det.wait_for_selector(".stat__row", timeout=15000)
                                
                                # Пытаемся переключиться на вкладку 1-го периода для точности
                                tab_p1 = det.locator('a[href*="match-statistics/1"]')
                                if await tab_p1.count() > 0:
                                    await tab_p1.first.click()
                                    await det.wait_for_timeout(1000)
                            except: pass

                            stat_rows = await det.locator(".stat__row").all()
                            total_sh, total_wh, total_pim = None, 0, 0
                            
                            for s_row in stat_rows:
                                cat_name = (await s_row.locator(".stat__categoryName").inner_text()).lower()
                                h_val = await s_row.locator(".stat__homeValue").inner_text()
                                a_val = await s_row.locator(".stat__awayValue").inner_text()
                                try:
                                    val_sum = int(h_val) + int(a_val)
                                except: continue

                                # Броски (только один раз - Shots on Goal)
                                if total_sh is None and any(x in cat_name for x in ["shots on goal", "броски в створ"]):
                                    total_sh = val_sum
                                
                                # Удаления (свистки)
                                if any(x in cat_name for x in ["penalties", "удаления", "2-min penalties"]):
                                    total_wh = val_sum
                                
                                # Штрафное время (PIM)
                                if any(x in cat_name for x in ["pim", "penalty minutes", "штрафное время"]):
                                    total_pim = val_sum

                            if total_sh is None:
                                print(f"      ❌ Нет данных по броскам.", flush=True)
                                continue

                            print(f"      📊 Итог P1: Бр={total_sh}, Штр={total_pim}м, Свист={total_wh}", flush=True)

                            # 3. ОТПРАВКА СИГНАЛА
                            if total_sh >= 13 and total_pim >= 2 and total_wh >= 1:
                                msg = (f"🚨 <b>СИГНАЛ: ПЕРЕРЫВ P1</b>\n"
                                       f"🏆 {cur_league}\n"
                                       f"🤝 {home} — {away}\n"
                                       f"━━━━━━━━━━━━━━━━━━\n"
                                       f"🥅 Счет P1: <b>{sc_h}:{sc_a}</b>\n"
                                       f"🎯 Броски (P1): <b>{total_sh}</b>\n"
                                       f"❌ Удаления (P1): <b>{total_wh}</b>\n"
                                       f"⏳ Штраф (P1): <b>{total_pim} мин</b>\n"
                                       f"━━━━━━━━━━━━━━━━━━\n"
                                       f"🕒 <i>Ждем гол во 2-м периоде...</i>")
                                await send_tg(msg)
                                TRACKED_MATCHES[m_id] = {"home": home, "away": away, "p1_total": sc_h + sc_a}
                                save_data()
                                print("      ✅ СИГНАЛ УШЕЛ!", flush=True)
                            else:
                                print("      ❌ Цифры не дотянули до стратегии.", flush=True)

                        except Exception as e:
                            print(f"      ⚠️ Ошибка: {e}", flush=True)
                        finally: await det.close()
                
                print(f"💤 Сплю 60 сек...", flush=True)
            except Exception as e:
                print(f"⚠️ Ошибка цикла: {e}", flush=True)
            
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
