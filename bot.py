import asyncio
import os
import re
import aiohttp
from playwright.async_api import async_playwright

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")

SENT_SIGNALS = set()
# Лиги, которые точно дают статсу (стартовый набор)
WHITE_LIST = {"NHL", "KHL", "SHL", "AHL", "ВХЛ", "МХЛ", "LIIGA"}
# Лиги, где статы точно НЕТ (чтобы не заходить в них второй раз)
BLACK_LIST = set()

async def send_tg(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        try:
            await session.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
        except Exception as e: print(f"ТГ ошибка: {e}")

async def main():
    print("--- 🧠 ЗАПУЩЕН САМООБУЧАЮЩИЙСЯ БОТ-СКАНЕР ---", flush=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...")
        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        while True:
            try:
                print(f"\n📡 Мониторинг. В белом списке: {len(WHITE_LIST)} лиг.", flush=True)
                await page.goto("https://www.flashscore.com/hockey/", timeout=60000)
                await page.wait_for_selector(".event__match", timeout=20000)
                
                rows = await page.locator(".event__header, .event__match").all()
                current_league = "Unknown"
                
                for row in rows:
                    classes = await row.get_attribute("class")
                    if "event__header" in classes:
                        title_node = row.locator(".event__title--name")
                        if await title_node.count() > 0:
                            current_league = await title_node.inner_text()
                        continue
                    
                    if "event__match" in classes:
                        # Если лига в черном списке — скипаем
                        if current_league in BLACK_LIST: continue
                        
                        # Проверка времени (1-й период или перерыв) и счета
                        stage = await row.locator(".event__stage").inner_text()
                        if "1" not in stage and "Break" not in stage: continue
                        
                        sc_h = await row.locator(".event__score--home").inner_text()
                        sc_a = await row.locator(".event__score--away").inner_text()
                        if not (sc_h.isdigit() and sc_a.isdigit()) or (int(sc_h) + int(sc_a)) > 1: continue
                        
                        m_id = (await row.get_attribute("id")).split("_")[-1]
                        if m_id in SENT_SIGNALS: continue

                        home = await row.locator(".event__participant--home").inner_text()
                        away = await row.locator(".event__participant--away").inner_text()
                        
                        # Если лига новая — идем на разведку!
                        is_scouting = current_league not in WHITE_LIST
                        print(f"{'🔎 СКАУТИНГ' if is_scouting else '✅ АНАЛИЗ'}: {home} - {away} ({current_league})", flush=True)
                        
                        detail_page = await context.new_page()
                        try:
                            # 1. Проверяем наличие СТАТИСТИКИ (броски)
                            await detail_page.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/0", timeout=30000)
                            await detail_page.wait_for_timeout(3000)
                            stats_text = await detail_page.locator("#detail").inner_text()
                            
                            sh_match = re.search(r"(\d+)\s*(Shots on Goal|Выстрелы по цели)\s*(\d+)", stats_text)
                            
                            if not sh_match and is_scouting:
                                print(f"   ❌ В лиге '{current_league}' нет статистики бросков. В черный список.", flush=True)
                                BLACK_LIST.add(current_league)
                                continue

                            # Если стата есть, а лиги нет в белом списке — добавляем!
                            if is_scouting:
                                WHITE_LIST.add(current_league)
                                await send_tg(f"🔥 <b>Новая лига со статистикой!</b>\nДобавлена в белый список: <code>{current_league}</code>")

                            total_shots = int(sh_match.group(1)) + int(sh_match.group(3)) if sh_match else 0
                            
                            # 2. Считаем УДАЛЕНИЯ (свистки) в Summary
                            await detail_page.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary", timeout=20000)
                            await detail_page.wait_for_timeout(2000)
                            incidents = await detail_page.locator(".smv__periodHeader:has-text('1st Period'), .smv__periodHeader:has-text('1-й период')").locator("xpath=following-sibling::div[1]").locator(".smv__incident:has-text('min'), .smv__incident:has-text('мин')").all()
                            whistles = len(incidents)

                            # ФИНАЛЬНОЕ УСЛОВИЕ (Твоя логика)
                            if whistles >= 1 and (total_shots >= 12 or total_shots == 0):
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
                        except Exception as e: print(f"Ошибка в деталях: {e}")
                        finally: await detail_page.close()
            except Exception as e: print(f"Ошибка цикла: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
