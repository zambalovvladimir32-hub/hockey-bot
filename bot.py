import asyncio
import os
import json
import re
import random
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
        except Exception: pass

# Функция для имитации человеческого ожидания
async def human_delay(min_sec=2, max_sec=5):
    await asyncio.sleep(random.uniform(min_sec, max_sec))

async def main():
    print(f"--- 🦾 БОТ V27: HUMAN IMITATOR MODE ---", flush=True)
    load_data()
    
    async with async_playwright() as p:
        proxy_settings = {"server": PROXY_URL} if PROXY_URL else None
        
        # Запуск браузера с кучей флагов для обхода защиты
        browser = await p.chromium.launch(
            headless=True,
            proxy=proxy_settings,
            args=[
                '--no-sandbox', 
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--use-fake-ui-for-media-stream',
                '--window-size=1920,1080'
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            device_scale_factor=1,
        )

        # Скрываем следы автоматизации на уровне движка
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        main_page = await context.new_page()
        
        while True:
            try:
                print("\n📡 Захожу на Flashscore...", flush=True)
                await main_page.goto("https://www.flashscore.com/hockey/", timeout=60000, wait_until="domcontentloaded")
                
                # Имитируем скролл страницы вниз, чтобы триггернуть подгрузку
                await main_page.mouse.wheel(0, 500)
                await human_delay(1, 2)
                
                await main_page.wait_for_selector(".event__match", timeout=30000)
                
                rows = await main_page.locator(".event__header, .event__match").all()
                cur_league = "Неизвестная лига"
                
                for row in rows:
                    cls = await row.get_attribute("class") or ""
                    
                    if "event__header" in cls:
                        cur_league = (await row.inner_text()).replace("\n", " ").strip()
                        continue
                    
                    if "event__match" in cls:
                        stage_el = row.locator(".event__stage")
                        if await stage_el.count() == 0: continue
                        stage = (await stage_el.inner_text()).lower()
                        
                        # Нам нужен только первый перерыв
                        if "break" not in stage and "перерыв" not in stage: continue
                        if any(x in stage for x in ["2nd", "3rd", "2-й", "3-й"]): continue
                        
                        m_id = (await row.get_attribute("id") or "").split("_")[-1]
                        if not m_id or m_id in TRACKED_MATCHES: continue

                        # Проверка счета 0:0, 1:0, 0:1
                        sc_h = await row.locator(".event__score--home").inner_text()
                        sc_a = await row.locator(".event__score--away").inner_text()
                        if not (sc_h.isdigit() and sc_a.isdigit()) or (int(sc_h) + int(sc_a)) > 1: continue

                        home = await row.locator(".event__participant--home").inner_text()
                        away = await row.locator(".event__participant--away").inner_text()
                        
                        print(f"   🎯 КАНДИДАТ: {home} - {away}", flush=True)
                        
                        # Открываем матч в новой вкладке
                        det = await context.new_page()
                        try:
                            # 1. Заходим в статистику
                            await det.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/0", timeout=40000)
                            
                            # Имитируем движение мыши к центру страницы
                            await det.mouse.move(960, 540)
                            await human_delay(3, 6) # Даем время на рендер таблицы

                            # Выкачиваем весь текст блока статистики
                            stat_content = await det.locator("#detail").inner_text()
                            
                            # Парсим цифры через Regex (ищем Shot, Penalties, PIM)
                            total_sh = 0
                            total_wh = 0
                            total_pim = 0
                            
                            lines = [l.strip() for l in stat_content.split("\n") if l.strip()]
                            for i, line in enumerate(lines):
                                l_low = line.lower()
                                # Броски (Shots on Goal)
                                if "shot" in l_low and "goal" in l_low and total_sh == 0:
                                    try: total_sh = int(lines[i-1]) + int(lines[i+1])
                                    except: pass
                                # Штрафы (PIM / Penalty Minutes)
                                if ("pim" in l_low or "penalty minutes" in l_low or "штраф" in l_low) and total_pim == 0:
                                    try: total_pim = int(lines[i-1]) + int(lines[i+1])
                                    except: pass
                                # Удаления (Penalties)
                                if ("penalties" in l_low or "удаления" in l_low) and "2-min" not in l_low and total_wh == 0:
                                    try: total_wh = int(lines[i-1]) + int(lines[i+1])
                                    except: pass

                            print(f"      📊 Итог: Бр={total_sh}, Штр={total_pim}, Свист={total_wh}", flush=True)

                            # Условия для сигнала
                            if total_sh >= 13 and total_pim >= 2 and total_wh >= 1:
                                msg = (f"🚨 <b>СИГНАЛ: ПЕРЕРЫВ P1</b>\n🏆 {cur_league}\n🤝 {home} — {away}\n"
                                       f"🎯 Броски: {total_sh} | ❌ Удаления: {total_wh} | ⏳ Штраф: {total_pim} мин\n"
                                       f"🕒 <i>Ждем гол во 2-м периоде!</i>")
                                await send_tg(msg)
                                TRACKED_MATCHES[m_id] = {"home": home, "away": away, "p1_total": int(sc_h) + int(sc_a)}
                                save_data()
                                print("      ✅ СИГНАЛ ОТПРАВЛЕН!", flush=True)
                            else:
                                print("      ❌ Цифры не дотянули.", flush=True)

                        except Exception as e:
                            print(f"      ⚠️ Ошибка: {e}", flush=True)
                        finally:
                            await det.close()
                
                print(f"💤 Сплю 60 сек...", flush=True)
                await asyncio.sleep(60)
            except Exception as e:
                print(f"⚠️ Ошибка цикла: {e}", flush=True)
                await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
