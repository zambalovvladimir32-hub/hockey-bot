import asyncio
import os
import re
import json
import aiohttp
from playwright.async_api import async_playwright

# --- КОНФИГ ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
DB_LEAGUES = "leagues.txt"
DB_MATCHES = "tracked_matches.json"

WHITE_LIST = {"NHL", "KHL", "SHL", "AHL", "ВХЛ", "МХЛ"}
BLACK_LIST = set()
TRACKED_MATCHES = {} # {match_id: {"home": str, "away": str, "p1_total": int}}

# --- РАБОТА С ФАЙЛАМИ ---
def save_data():
    with open(DB_LEAGUES, "w", encoding="utf-8") as f:
        f.write(",".join(WHITE_LIST) + "|" + ",".join(BLACK_LIST))
    with open(DB_MATCHES, "w", encoding="utf-8") as f:
        json.dump(TRACKED_MATCHES, f)

def load_data():
    global WHITE_LIST, BLACK_LIST, TRACKED_MATCHES
    if os.path.exists(DB_LEAGUES):
        with open(DB_LEAGUES, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if "|" in content:
                w, b = content.split("|")
                if w: WHITE_LIST.update(w.split(","))
                if b: BLACK_LIST.update(b.split(","))
    if os.path.exists(DB_MATCHES):
        with open(DB_MATCHES, "r", encoding="utf-8") as f:
            TRACKED_MATCHES = json.load(f)

# --- TELEGRAM ---
async def send_tg(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        try:
            await session.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
        except Exception as e: print(f"ТГ ошибка: {e}")

# --- ПРОВЕРКА РЕЗУЛЬТАТА (ПОСЛЕ P2) ---
async def check_results(context):
    to_delete = []
    for m_id, data in TRACKED_MATCHES.items():
        page = await context.new_page()
        try:
            await page.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary", timeout=30000)
            status = await page.locator(".detailScore__status").inner_text()
            
            # Проверяем, если начался перерыв после P2, начался P3 или матч окончен
            if any(x in status for x in ["Break", "3rd Period", "Finished", "Перерыв"]):
                # Берем текущий общий счет
                scores = await page.locator(".detailScore__wrapper").inner_text()
                # Извлекаем цифры счета (например "2 - 1")
                nums = re.findall(r"\d+", scores)
                if len(nums) >= 2:
                    current_total = int(nums[0]) + int(nums[1])
                    if current_total > data['p1_total']:
                        msg = f"✅ <b>ГОЛ ПОЙМАН!</b>\n🤝 {data['home']} — {data['away']}\nСтатистика сработала во 2-м периоде."
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
    print("--- 🦾 БОТ-АНАЛИТИК: ТОЛЬКО СТАТИСТИКА ---", flush=True)
    load_data()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        context = await browser.new_context(user_agent="Mozilla/5.0...")
        main_page = await context.new_page()
        
        while True:
            try:
                # 1. Проверяем доехавшие результаты
                if TRACKED_MATCHES: await check_results(context)

                # 2. Ищем новые сигналы
                print("\n📡 Поиск матчей в перерыве P1...", flush=True)
                await main_page.goto("https://www.flashscore.com/hockey/", timeout=60000)
                await main_page.wait_for_selector(".event__match", timeout=20000)
                
                rows = await main_page.locator(".event__header, .event__match").all()
                cur_league = "Unknown"
                
                for row in rows:
                    cls = await row.get_attribute("class")
                    if "event__header" in cls:
                        title = row.locator(".event__title--name")
                        if await title.count() > 0: cur_league = await title.inner_text()
                        continue
                    
                    if "event__match" in cls:
                        if cur_league in BLACK_LIST: continue
                        
                        # ФИЛЬТР: Только перерыв 1-го периода
                        stage = await row.locator(".event__stage").inner_text()
                        if "Break" not in stage or "1st" not in stage: continue
                        
                        m_id = (await row.get_attribute("id")).split("_")[-1]
                        if m_id in TRACKED_MATCHES: continue

                        sc_h = int(await row.locator(".event__score--home").inner_text())
                        sc_a = int(await row.locator(".event__score--away").inner_text())
                        if (sc_h + sc_a) > 1: continue

                        home = await row.locator(".event__participant--home").inner_text()
                        away = await row.locator(".event__participant--away").inner_text()
                        
                        # Детальный разбор
                        det = await context.new_page()
                        try:
                            # Статистика бросков и минут
                            await det.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/0", timeout=30000)
                            await det.wait_for_timeout(3000)
                            content = await det.locator("#detail").inner_text()
                            
                            sh = re.search(r"(\d+)\s*(Shots on Goal|Выстрелы по цели|Střely)\s*(\d+)", content)
                            pim = re.search(r"(\d+)\s*(Penalty Minutes|Штрафное время|Trestné minuty)\s*(\d+)", content)
                            
                            if not sh:
                                if cur_league not in WHITE_LIST:
                                    BLACK_LIST.add(cur_league); save_data()
                                continue

                            total_sh = int(sh.group(1)) + int(sh.group(3))
                            total_pim = int(pim.group(1)) + int(pim.group(3)) if pim else 0
                            
                            # Лента событий (свистки)
                            await det.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary", timeout=20000)
                            await det.wait_for_timeout(2000)
                            wh_list = await det.locator(".smv__periodHeader:has-text('1st'), .smv__periodHeader:has-text('1-й')").locator("xpath=following-sibling::div[1]").locator(".smv__incident:has-text('min'), .smv__incident:has-text('мин')").all()
                            total_wh = len(wh_list)

                            # ПРОВЕРКА СТРАТЕГИИ: Счет <=1, Броски >=13, Штрафы >=2, Свистки >=1
                            if total_sh >= 13 and total_pim >= 2 and total_wh >= 1:
                                if cur_league not in WHITE_LIST:
                                    WHITE_LIST.add(cur_league); save_data()
                                    await send_tg(f"🎓 <b>Новая лига:</b> {cur_league}")

                                msg = (f"🚨 <b>СИГНАЛ: ПЕРЕРЫВ P1</b>\n"
                                       f"🏆 {cur_league}\n"
                                       f"🤝 {home} — {away}\n"
                                       f"━━━━━━━━━━━━━━━━━━\n"
                                       f"🥅 Счет P1: <b>{sc_h}:{sc_a}</b>\n"
                                       f"🎯 Броски: <b>{total_sh}</b>\n"
                                       f"❌ Удаления: <b>{total_wh}</b>\n"
                                       f"⏳ Штраф: <b>{total_pim} мин</b>\n"
                                       f"━━━━━━━━━━━━━━━━━━\n"
                                       f"🕒 <i>Ждем гол во 2-м периоде...</i>")
                                await send_tg(msg)
                                
                                TRACKED_MATCHES[m_id] = {"home": home, "away": away, "p1_total": sc_h + sc_a}
                                save_data()
                        except: pass
                        finally: await det.close()
            except: pass
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
