import asyncio
import os
import json
import re
import aiohttp
from playwright.async_api import async_playwright

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
    print(f"--- 🦾 БОТ V40: ЧЕШСКИЙ ПРОРЫВ ---", flush=True)
    load_data()
    
    async with async_playwright() as p:
        # Пытаемся запустить браузер с прокси
        proxy_cfg = {"server": PROXY_URL} if PROXY_URL else None
        browser = await p.chromium.launch(headless=True, proxy=proxy_cfg, args=['--no-sandbox'])
        
        # Создаем контекст с эмуляцией реального чешского пользователя
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="cs-CZ",
            timezone_id="Europe/Prague"
        )

        page = await context.new_page()
        # Блокируем картинки, чтобы не тратить время прокси
        await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "font"] else route.continue_())

        while True:
            try:
                print(f"\n📡 Пробую зайти на Flashscore.cz (Live)...", flush=True)
                
                # Используем чешский домен и режим commit (самый быстрый)
                try:
                    await page.goto("https://www.flashscore.cz/hokej/?s=2", timeout=60000, wait_until="commit")
                    await asyncio.sleep(10) # Даем время JS отрисовать таблицу
                except Exception as e:
                    print(f"❌ Опять таймаут: {e}. Прокси не тянет чешский домен?", flush=True)
                    await asyncio.sleep(5)
                    continue

                # Ищем матчи по разным признакам
                match_elements = await page.locator(".event__match, [id^='g_4_']").all()
                print(f"📊 Элементов найдено: {len(match_elements)}", flush=True)

                if len(match_elements) == 0:
                    # Если пусто — выводим что видим
                    snippet = await page.evaluate("document.body.innerText.substring(0, 300)")
                    print(f"🧐 Внутри страницы: {snippet.replace(chr(10), ' ')}", flush=True)
                    continue

                for row in match_elements:
                    try:
                        text = await row.inner_text()
                        if "pauza" not in text.lower() and "перерыв" not in text.lower() and "break" not in text.lower():
                            continue
                        
                        m_id = (await row.get_attribute("id")).split("_")[-1]
                        if m_id in TRACKED_MATCHES: continue

                        # Читаем статку (быстрый переход)
                        det = await context.new_page()
                        try:
                            await det.goto(f"https://www.flashscore.cz/zapas/{m_id}/#/prehled/statistiky/0", timeout=30000, wait_until="commit")
                            await asyncio.sleep(5)
                            
                            stat_text = await det.evaluate("document.body.innerText")
                            
                            # Поиск по чешским ключам (как на твоем скрине)
                            sh = re.search(r"(\d+)[\s\n]+(?:Střely na branku|Shots on Goal)[\s\n]+(\d+)", stat_text, re.I)
                            if sh:
                                t_sh = int(sh.group(1)) + int(sh.group(2))
                                print(f"✅ Матч {m_id}: Броски {t_sh}", flush=True)
                                
                                if t_sh >= 13:
                                    # Достаем названия команд
                                    teams = re.findall(r"([A-Za-z\s]+)\d+:\d+", stat_text)
                                    name = teams[0] if teams else m_id
                                    await send_tg(f"🚨 <b>СИГНАЛ P1</b>\n🎯 Броски: {t_sh}\nID: {m_id}")
                                    TRACKED_MATCHES[m_id] = {"id": m_id}
                                    save_data()
                        except: pass
                        finally: await det.close()

                    except: continue

                print(f"💤 Сплю 2 минуты...", flush=True)
                await asyncio.sleep(120)
            except Exception as e:
                print(f"⚠️ Ошибка цикла: {e}", flush=True)
                await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
