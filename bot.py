import asyncio
import os
import re
import aiohttp
from playwright.async_api import async_playwright

# Настройки из Railway
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")

SENT_SIGNALS = set()

# --- ⚪️ ТВОЙ БЕЛЫЙ СПИСОК ЛИГ ---
# Впиши сюда названия или части названий лиг, которые тебе нужны
WHITE_LIST = [
    "NHL", "KHL", "SHL", "AHL", "ВХЛ", "МХЛ", 
    "LIIGA", "MESTIS", "EXTRA LIGA", "CHAMPIONS LEAGUE", 
    "DEL", "ICE HOCKEY LEAGUE"
]

async def send_tg(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        try:
            await session.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
        except Exception as e: print(f"Ошибка ТГ: {e}")

async def main():
    print("--- 🎯 БОТ: ФИЛЬТР ЛИГ + СЧЕТЧИК СВИСТКОВ ЗАПУЩЕН ---", flush=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, 
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        while True:
            try:
                print("\n📡 Мониторинг линий...", flush=True)
                await page.goto("https://www.flashscore.com/hockey/", timeout=60000)
                await page.wait_for_selector(".event__match", timeout=20000)
                
                # Собираем лиги и матчи
                elements = await page.locator(".event__header, .event__match").all()
                current_league = "Unknown"
                
                for el in elements:
                    classes = await el.get_attribute("class")
                    
                    # 1. Запоминаем текущую лигу
                    if "event__header" in classes:
                        title_node = el.locator(".event__title--name")
                        if await title_node.count() > 0:
                            current_league = await title_node.inner_text()
                        continue
                    
                    # 2. Обрабатываем матч
                    if "event__match" in classes:
                        # Фильтр по белому списку
                        if not any(l.upper() in current_league.upper() for l in WHITE_LIST):
                            continue
                            
                        # Проверка времени (1-й период или перерыв)
                        stage = await el.locator(".event__stage").inner_text()
                        if "1" not in stage and "Break" not in stage:
                            continue
                            
                        # Проверка счета (<= 1 гола)
                        sc_h = await el.locator(".event__score--home").inner_text()
                        sc_a = await el.locator(".event__score--away").inner_text()
                        
                        if not (sc_h.isdigit() and sc_a.isdigit()): continue
                        if (int(sc_h) + int(sc_a)) > 1: continue
                        
                        m_id = (await el.get_attribute("id")).split("_")[-1]
                        if m_id in SENT_SIGNALS: continue

                        home = await el.locator(".event__participant--home").inner_text()
                        away = await el.locator(".event__participant--away").inner_text()
                        
                        print(f"🔍 Нашел матч: {home} - {away} ({current_league})", flush=True)
                        
                        # 3. Идем внутрь за удалений и бросками
                        detail_page = await context.new_page()
                        try:
                            # Считаем именно УДАЛЕНИЯ (свистки) во вкладке Summary
                            await detail_page.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary", timeout=30000)
                            await detail_page.wait_for_timeout(3000)
                            
                            # Находим блок 1-го периода и считаем иконки удалений (incident--penalty)
                            # Мы ищем все элементы событий, где есть текст "min" или "мин" в 1-м периоде
                            incidents = await detail_page.locator(".smv__periodHeader:has-text('1st Period'), .smv__periodHeader:has-text('1-й период')").locator("xpath=following-sibling::div[1]").locator(".smv__incident:has-text('min'), .smv__incident:has-text('мин')").all()
                            whistles_count = len(incidents)

                            # Считаем БРОСКИ во вкладке Statistics
                            await detail_page.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/0", timeout=20000)
                            await detail_page.wait_for_timeout(2000)
                            stats_text = await detail_page.locator("#detail").inner_text()
                            sh_match = re.search(r"(\d+)\s*(Shots on Goal|Выстрелы по цели)\s*(\d+)", stats_text)
                            total_shots = int(sh_match.group(1)) + int(sh_match.group(3)) if sh_match else 0

                            print(f"   📊 Свистки: {whistles_count} | Броски: {total_shots}", flush=True)

                            # Условие: Удалений (свистков) >= 1 и Бросков >= 12
                            if whistles_count >= 1 and (total_shots >= 12 or total_shots == 0):
                                msg = (f"🏒 <b>{current_league}</b>\n"
                                       f"🤝 <b>{home} — {away}</b>\n"
                                       f"━━━━━━━━━━━━━━━━━━\n"
                                       f"❌ Удалений (свистков): <b>{whistles_count}</b>\n"
                                       f"🎯 Бросков в створ: <b>{total_shots}</b>\n"
                                       f"🥅 Счет P1: <b>{sc_h}:{sc_a}</b>\n"
                                       f"━━━━━━━━━━━━━━━━━━\n"
                                       f"✅ <i>Матч отфильтрован по лиге и удалениям!</i>")
                                
                                await send_tg(msg)
                                SENT_SIGNALS.add(m_id)
                                print(f"🚀 СИГНАЛ ОТПРАВЛЕН!")
                        except Exception as e:
                            print(f"   ⚠️ Ошибка в деталях: {e}")
                        finally:
                            await detail_page.close()
                            
            except Exception as e:
                print(f"⚠️ Ошибка цикла: {e}")
                
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
