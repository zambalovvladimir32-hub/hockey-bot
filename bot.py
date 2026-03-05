import asyncio
import os
import json
import re
from playwright.async_api import async_playwright

PROXY_URL = os.getenv("PROXY_URL") 
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
DB_MATCHES = "tracked_matches.json"

TRACKED_MATCHES = {}

def save_data():
    with open(DB_MATCHES, "w", encoding="utf-8") as f:
        json.dump(TRACKED_MATCHES, f)

async def send_tg(text):
    if not TOKEN or not CHAT_ID: return
    import aiohttp
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        try: await session.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
        except: pass

async def main():
    print(f"--- 🦾 БОТ V49: MOBILE SPEEDSTER ---", flush=True)
    
    async with async_playwright() as p:
        proxy_cfg = {"server": PROXY_URL}
        browser = await p.chromium.launch(headless=True, proxy=proxy_cfg, args=['--no-sandbox'])
        
        # Эмулируем мобильный телефон (это важно для m-версии)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
            viewport={'width': 375, 'height': 667}
        )

        page = await context.new_page()
        # Блокируем всё, что не текст
        await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "font", "media"] else route.continue_())

        while True:
            try:
                print(f"\n📡 Захожу на мобильный Flashscore...", flush=True)
                
                # Идем на мобильную версию (хоккей лайв)
                # wait_until="commit" - работаем сразу, как только пошел ответ от сервера
                await page.goto("https://m.flashscore.ru/hockey/?s=2", timeout=60000, wait_until="commit")
                await asyncio.sleep(10) # Даем JS время отрисовать матчи

                # На мобилке селекторы другие
                matches = await page.locator("#default-live-table .event__match").all()
                print(f"📊 Матчей в лайве: {len(matches)}", flush=True)
                
                if len(matches) == 0:
                    # Если через мобилку пусто, попробуем еще раз через 30 сек
                    print("🧐 Пока пусто или сайт не прогрузился.", flush=True)
                    await asyncio.sleep(30)
                    continue

                for row in matches:
                    try:
                        text = (await row.inner_text()).lower()
                        if "перерыв" not in text: continue
                        
                        m_id = (await row.get_attribute("id")).split("_")[-1]
                        if m_id in TRACKED_MATCHES: continue

                        print(f"   🎯 Поймал перерыв! ID: {m_id}. Лезу внутрь...", flush=True)

                        # Статистика на мобилке тоже по другому адресу
                        det = await context.new_page()
                        try:
                            # Прямой линк на статистику
                            await det.goto(f"https://m.flashscore.ru/match/{m_id}/#/match-summary/match-statistics/0", timeout=30000, wait_until="commit")
                            await asyncio.sleep(5)
                            
                            stat_text = await det.evaluate("document.body.innerText")
                            
                            # Парсим броски и штрафы
                            sh = re.search(r"Броски в створ\s+(\d+)\s+(\d+)", stat_text)
                            wh = re.search(r"Удаления\s+(\d+)\s+(\d+)", stat_text)
                            pim = re.search(r"Штрафное время\s+(\d+)\s+(\d+)", stat_text)

                            if sh:
                                t_sh = int(sh.group(1)) + int(sh.group(2))
                                t_wh = (int(wh.group(1)) + int(wh.group(2))) if wh else 0
                                t_pim = (int(pim.group(1)) + int(pim.group(2))) if pim else 0
                                
                                print(f"      📊 Стата: Бр={t_sh}, Свист={t_wh}, Штр={t_pim}", flush=True)

                                if t_sh >= 13 and t_pim >= 2 and t_wh >= 1:
                                    await send_tg(f"🚨 <b>СИГНАЛ P1</b>\n🎯 Броски: {t_sh}\n❌ Удаления: {t_wh}\nID: {m_id}")
                                    TRACKED_MATCHES[m_id] = True
                                    save_data()
                        except: pass
                        finally: await det.close()

                    except: continue

                await asyncio.sleep(60)
            except Exception as e:
                print(f"⚠️ Ошибка: {e}", flush=True)
                await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(main())
