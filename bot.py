import asyncio
import os
import re
import aiohttp
from playwright.async_api import async_playwright

# --- НАСТРОЙКИ ИЗ RAILWAY ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
DB_FILE = "leagues.txt"

# Начальные лиги (костяк)
WHITE_LIST = {"NHL", "KHL", "SHL", "AHL", "ВХЛ", "МХЛ", "LIIGA"}
BLACK_LIST = set()
SENT_SIGNALS = set()

# --- ФУНКЦИИ ПАМЯТИ ---
def save_db():
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            f.write(",".join(WHITE_LIST) + "|" + ",".join(BLACK_LIST))
    except Exception as e:
        print(f"Ошибка сохранения БД: {e}")

def load_db():
    global WHITE_LIST, BLACK_LIST
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if "|" in content:
                    w, b = content.split("|")
                    if w: WHITE_LIST.update(w.split(","))
                    if b: BLACK_LIST.update(b.split(","))
            print(f"✅ База загружена. Белых: {len(WHITE_LIST)}, Черных: {len(BLACK_LIST)}")
        except Exception as e:
            print(f"Ошибка загрузки БД: {e}")

# --- РАБОТА С TELEGRAM ---
async def send_tg(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        try:
            await session.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
        except Exception as e: print(f"ТГ ошибка: {e}")

# --- ГЛАВНАЯ ЛОГИКА ---
async def main():
    print("--- 🤖 ЗАПУСК АВТОНОМНОГО СКАНЕРА V3.0 ---", flush=True)
    load_db()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, 
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        while True:
            try:
                print(f"\n📡 Сканирование. В базе {len(WHITE_LIST)} лиг.", flush=True)
                await page.goto("https://www.flashscore.com/hockey/", timeout=60000)
                await page.wait_for_selector(".event__match", timeout=20000)
                
                elements = await page.locator(".event__header, .event__match").all()
                current_league = "Unknown"
                
                for el in elements:
                    classes = await el.get_attribute("class")
                    
                    if "event__header" in classes:
                        title_node = el.locator(".event__title--name")
                        if await title_node.count() > 0:
                            current_league = await title_node.inner_text()
                        continue
                    
                    if "event__match" in classes:
                        if current_league in BLACK_LIST: continue
                        
                        # Проверка времени и счета
                        stage = await el.locator(".event__stage").inner_text()
                        if "1" not in stage and "Break" not in stage: continue
                        
                        sc_h = await el.locator(".event__score--home").inner_text()
                        sc_a = await el.locator(".event__score--away").inner_text()
                        if not (sc_h.isdigit() and sc_a.isdigit()): continue
                        if (int(sc_h) + int(sc_a)) > 1: continue
                        
                        m_id = (await el.get_attribute("id")).split("_")[-1]
                        if m_id in SENT_SIGNALS: continue

                        home = await el.locator(".event__participant--home").inner_text()
                        away = await el.locator(".event__participant--away").inner_text()
                        
                        is_new = current_league not in WHITE_LIST
                        print(f"{'🔎 СКАУТ' if is_new else '✅ АНАЛИЗ'}: {home} - {away} ({current_league})", flush=True)
                        
                        detail_page = await context.new_page()
                        try:
                            # 1. Проверяем БРОСКИ
                            await detail_page.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/0", timeout=30000)
                            await detail_page.wait_for_timeout(3000)
                            stats_text = await detail_page.locator("#detail").inner_text()
                            
                            sh_match = re.search(r"(\d+)\s*(Shots on Goal|Выстрелы по цели|Střely)\s*(\d+)", stats_text)
                            
                            if not sh_match:
                                if is_new:
                                    print(f"   ❌ Нет статы. Бан лиги: {current_league}")
                                    BLACK_LIST.add(current_league)
                                    save_db()
                                continue

                            # Если стата есть — легализуем лигу
                            if is_new:
                                WHITE_LIST.add(current_league)
                                save_db()
                                await send_tg(f"🎓 <b>Обучение:</b> Новая лига добавлена в белый список:\n<code>{current_league}</code>")

                            total_shots = int(sh_match.group(1)) + int(sh_match.group(3))
                            
                            # 2. Считаем СВИСТКИ (Удаления)
                            await detail_page.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary", timeout=20000)
                            await detail_page.wait_for_timeout(2000)
                            # Ищем все элементы штрафов в 1-м периоде
                            incidents = await detail_page.locator(".smv__periodHeader:has-text('1st Period'), .smv__periodHeader:has-text('1-й период')").locator("xpath=following-sibling::div[1]").locator(".smv__incident:has-text('min'), .smv__incident:has-text('мин')").all()
                            whistles = len(incidents)

                            # ФИНАЛЬНОЕ УСЛОВИЕ
                            if whistles >= 1 and total_shots >= 12:
                                msg = (f"🥅 <b>{current_league}</b>\n"
                                       f"🤝 <b>{home} — {away}</b>\n"
                                       f"━━━━━━━━━━━━━━━━━━\n"
                                       f"❌ Удалений (свистков): <b>{whistles}</b>\n"
                                       f"🎯 Бросков в створ: <b>{total_shots}</b>\n"
                                       f"🥅 Счет P1: <b>{sc_h}:{sc_a}</b>\n"
                                       f"━━━━━━━━━━━━━━━━━━\n"
                                       f"✅ <i>Сигнал по твоей стратегии!</i>")
                                await send_tg(msg)
                                SENT_SIGNALS.add(m_id)
                                print(f"🚀 СИГНАЛ ОТПРАВЛЕН: {home}-{away}")
                        except Exception as e: print(f"Ошибка в матче: {e}")
                        finally: await detail_page.close()
            except Exception as e:
                print(f"⚠️ Ошибка цикла: {e}")
            
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
