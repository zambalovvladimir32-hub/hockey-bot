import asyncio
import os
import json
import re
import aiohttp
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
            TRACKED_MATCHES = json.load(f)

async def send_tg(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        try:
            await session.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
        except Exception as e: print(f"ТГ ошибка: {e}", flush=True)

# --- ПРОВЕРКА РЕЗУЛЬТАТА (ЗАШЛО / МИМО) ---
async def check_results(context):
    to_delete = []
    for m_id, data in TRACKED_MATCHES.items():
        page = await context.new_page()
        try:
            await page.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary", timeout=30000)
            status = await page.locator(".detailScore__status").inner_text()
            
            # Проверяем, наступил ли конец 2-го периода или матч завершен
            if any(x in status for x in ["Break", "3rd", "3-й", "Finished", "Перерыв", "Завершен"]):
                scores = await page.locator(".detailScore__wrapper").inner_text()
                nums = re.findall(r"\d+", scores)
                if len(nums) >= 2:
                    current_total = int(nums[0]) + int(nums[1])
                    if current_total > data['p1_total']:
                        msg = f"✅ <b>ГОЛ ПОЙМАН!</b>\n🤝 {data['home']} — {data['away']}\nВторой период принес результат! 🚀"
                    else:
                        msg = f"❌ <b>БЕЗ ГОЛОВ</b>\n🤝 {data['home']} — {data['away']}\nВторой период прошел всухую."
                    
                    await send_tg(msg)
                    to_delete.append(m_id)
        except Exception: pass
        finally: await page.close()
    
    for m_id in to_delete: del TRACKED_MATCHES[m_id]
    if to_delete: save_data()

# --- ОСНОВНОЙ ПАРСЕР ---
async def main():
    print("--- 🦾 БОТ V22: КОНТРОЛЬ ПЕРВОГО ПЕРЕРЫВА ---", flush=True)
    load_data()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        context = await browser.new_context(user_agent="Mozilla/5.0...")
        main_page = await context.new_page()
        
        while True:
            try:
                if TRACKED_MATCHES: 
                    await check_results(context)

                print("\n📡 Обновляю Flashscore...", flush=True)
                await main_page.goto("https://www.flashscore.com/hockey/", timeout=60000)
                await main_page.wait_for_selector(".event__match", timeout=20000)
                
                rows = await main_page.locator(".event__header, .event__match").all()
                cur_league = "Неизвестная лига"
                matches_checked = 0
                
                for row in rows:
                    cls = await row.get_attribute("class")
                    
                    # 1. ЗАХВАТ ЛИГИ
                    if "event__header" in cls:
                        try:
                            l_text = await row.evaluate("el => el.textContent")
                            parts = [p.strip() for p in l_text.split('\n') if p.strip()]
                            cur_league = " - ".join(parts[:2]) if len(parts) >= 2 else parts[0]
                        except: pass
                        continue
                    
                    if "event__match" in cls:
                        matches_checked += 1
                        
                        stage_loc = row.locator(".event__stage")
                        if await stage_loc.count() == 0: continue
                        stage = await stage_loc.inner_text()
                        if not stage: continue
                        stage_lower = stage.lower()
                        
                        # Проверка: строго перерыв и отсутствие "2-й" в строке статуса
                        if not ("break" in stage_lower or "перерыв" in stage_lower): continue
                        if any(x in stage_lower for x in ["2nd", "3rd", "2-й", "3-й"]): continue
                        
                        m_id = (await row.get_attribute("id")).split("_")[-1]
                        if m_id in TRACKED_MATCHES: continue

                        # Проверка счета (сумма голов <= 1)
                        sc_h_loc = row.locator(".event__score--home")
                        sc_a_loc = row.locator(".event__score--away")
                        if await sc_h_loc.count() == 0 or await sc_a_loc.count() == 0: continue

                        sc_h_txt, sc_a_txt = await sc_h_loc.inner_text(), await sc_a_loc.inner_text()
                        if not sc_h_txt.strip().isdigit() or not sc_a_txt.strip().isdigit(): continue
                        
                        sc_h, sc_a = int(sc_h_txt.strip()), int(sc_a_txt.strip())
                        if (sc_h + sc_a) > 1: continue

                        home = await row.locator(".event__participant--home").inner_text()
                        away = await row.locator(".event__participant--away").inner_text()
                        
                        print(f"   🔍 КАНДИДАТ: {home.strip()} - {away.strip()} (Счет: {sc_h}:{sc_a} | {cur_league})", flush=True)
                        
                        det = await context.new_page()
                        try:
                            # 2. ПРОВЕРКА ВНУТРИ МАТЧА: НЕ НАЧАЛСЯ ЛИ 2-Й ПЕРИОД?
                            await det.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary", timeout=20000)
                            await det.wait_for_timeout(2000)
                            
                            # Если видим заголовок 2-го периода — уходим, это уже не наш клиент
                            headers = await det.locator(".smv__periodHeader").all_inner_texts()
                            if len(headers) > 1 or any("2nd" in h or "2-й" in h for h in headers):
                                print("      ❌ Пропуск: Обнаружен 2-й период в ленте.", flush=True)
                                continue

                            # 3. СБОР СТАТИСТИКИ (РЕГЕКС)
                            await det.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/0", timeout=30000)
                            await det.wait_for_timeout(3000)
                            
                            content = await det.evaluate("document.body.innerText")
                            
                            total_sh = None
                            total_wh = None
                            total_pim = None
                            
                            # Броски в створ ( Regex ищет паттерн: число - название - число )
                            m_sh = re.search(r"(\d+)[\s\n]*(Shots on Goal|Броски в створ|Střely на|Střely na branku|Střely)[\s\n]*(\d+)", content, re.IGNORECASE)
                            if m_sh: total_sh = int(m_sh.group(1)) + int(m_sh.group(3))

                            # Удаления (свистки)
                            m_wh = re.search(r"(\d+)[\s\n]*(Penalties|Удаления|Vyloučení|2-min penalties)[\s\n]*(\d+)", content, re.IGNORECASE)
                            if m_wh: total_wh = int(m_wh.group(1)) + int(m_wh.group(3))

                            # Штрафные минуты (PIM)
                            m_pim = re.search(r"(\d+)[\s\n]*(PIM|Penalty Minutes|Штрафное время|Trestné minuty|Trestné min\.)[\s\n]*(\d+)", content, re.IGNORECASE)
                            if m_pim: total_pim = int(m_pim.group(1)) + int(m_pim.group(3))

                            if total_sh is None:
                                print(f"      ❌ Нет статы бросков за P1.", flush=True)
                                continue

                            total_pim = total_pim or 0
                            total_wh = total_wh or 0

                            print(f"      📊 Итог P1: Броски={total_sh}, Штрафы={total_pim}м, Свистки={total_wh}", flush=True)

                            # --- КРИТЕРИИ СИГНАЛА ---
                            if total_sh >= 13 and total_pim >= 2 and total_wh >= 1:
                                msg = (f"🚨 <b>СИГНАЛ: ПЕРЕРЫВ P1</b>\n"
                                       f"🏆 {cur_league}\n"
                                       f"🤝 {home.strip()} — {away.strip()}\n"
                                       f"━━━━━━━━━━━━━━━━━━\n"
                                       f"🥅 Счет P1: <b>{sc_h}:{sc_a}</b>\n"
                                       f"🎯 Броски (P1): <b>{total_sh}</b>\n"
                                       f"❌ Удаления (P1): <b>{total_wh}</b>\n"
                                       f"⏳ Штраф (P1): <b>{total_pim} мин</b>\n"
                                       f"━━━━━━━━━━━━━━━━━━\n"
                                       f"🕒 <i>Ждем гол во 2-м периоде... Отчет придет в канал!</i>")
                                await send_tg(msg)
                                
                                TRACKED_MATCHES[m_id] = {"home": home.strip(), "away": away.strip(), "p1_total": sc_h + sc_a}
                                save_data()
                                print("      ✅ СИГНАЛ В ТЕЛЕГРАМЕ!", flush=True)
                            else:
                                print("      ❌ Пропуск по цифрам.", flush=True)
                        except Exception as e:
                            print(f"      ⚠️ Ошибка в деталях: {e}", flush=True)
                        finally: await det.close()
                
                print(f"💤 Проверено: {matches_checked}. Сплю 60 сек...", flush=True)
            except Exception as e:
                print(f"⚠️ Ошибка цикла: {e}", flush=True)
            
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
