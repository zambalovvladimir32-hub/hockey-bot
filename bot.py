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

def load_data():
    """Загрузка отслеживаемых матчей при старте"""
    global TRACKED_MATCHES
    if os.path.exists(DB_MATCHES):
        try:
            with open(DB_MATCHES, "r", encoding="utf-8") as f:
                TRACKED_MATCHES = json.load(f)
            print(f"📁 Загружено {len(TRACKED_MATCHES)} отслеживаемых матчей")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки БД: {e}")
            TRACKED_MATCHES = {}

def save_data():
    """Сохранение отслеживаемых матчей"""
    try:
        with open(DB_MATCHES, "w", encoding="utf-8") as f:
            json.dump(TRACKED_MATCHES, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Ошибка сохранения БД: {e}")

async def send_tg(text):
    """Отправка сообщения в Telegram"""
    if not TOKEN or not CHAT_ID:
        print("⚠️ Не настроены TOKEN или CHAT_ID")
        return
    import aiohttp
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"  # Исправлено: убран пробел
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json={
                "chat_id": CHAT_ID, 
                "text": text, 
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }) as resp:
                if resp.status != 200:
                    print(f"⚠️ Ошибка Telegram: {resp.status}")
        except Exception as e:
            print(f"⚠️ Ошибка отправки TG: {e}")

async def main():
    print(f"--- 🦾 БОТ V50: MOBILE SPEEDSTER (FIXED) ---", flush=True)
    
    # Загружаем данные при старте
    load_data()
    
    async with async_playwright() as p:
        proxy_cfg = {"server": PROXY_URL} if PROXY_URL else None
        browser = await p.chromium.launch(
            headless=True, 
            proxy=proxy_cfg, 
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15",
            viewport={'width': 375, 'height': 667},
            locale='ru-RU'
        )

        page = await context.new_page()
        # Блокируем тяжелый контент для скорости
        await page.route("**/*", lambda route: route.abort() 
            if route.request.resource_type in ["image", "font", "media", "stylesheet"] 
            else route.continue_())

        while True:
            try:
                print(f"\n📡 Захожу на мобильный Flashscore...", flush=True)
                
                # Исправлено: убран пробел в URL
                await page.goto(
                    "https://m.flashscore.ru/hockey/?s=2", 
                    timeout=60000, 
                    wait_until="domcontentloaded"  # Быстрее чем commit
                )
                await asyncio.sleep(8)  # Уменьшили с 10 до 8

                matches = await page.locator("#default-live-table .event__match").all()
                print(f"📊 Матчей в лайве: {len(matches)}", flush=True)
                
                if len(matches) == 0:
                    print("🧐 Пока пусто или сайт не прогрузился.", flush=True)
                    await asyncio.sleep(30)
                    continue

                for row in matches:
                    try:
                        text = (await row.inner_text()).lower()
                        if "перерыв" not in text:
                            continue
                        
                        match_id_attr = await row.get_attribute("id")
                        if not match_id_attr:
                            continue
                            
                        m_id = match_id_attr.split("_")[-1]
                        if m_id in TRACKED_MATCHES:
                            continue

                        print(f"   🎯 Поймал перерыв! ID: {m_id}. Лезу внутрь...", flush=True)

                        # Открываем статистику в новой вкладке
                        det = await context.new_page()
                        try:
                            # Исправлено: убран пробел в URL
                            stat_url = f"https://m.flashscore.ru/match/{m_id}/#/match-summary/match-statistics/0"
                            await det.goto(stat_url, timeout=30000, wait_until="domcontentloaded")
                            await asyncio.sleep(4)  # Уменьшили с 5 до 4
                            
                            stat_text = await det.evaluate("document.body.innerText")
                            
                            # Безопасный парсинг с проверками
                            sh = re.search(r"Броски в створ\s+(\d+)\s+(\d+)", stat_text)
                            if not sh:
                                print(f"      ⚠️ Статистика бросков не найдена для {m_id}")
                                continue

                            t_sh = int(sh.group(1)) + int(sh.group(2))
                            
                            # Опциональные параметры
                            wh = re.search(r"Удаления\s+(\d+)\s+(\d+)", stat_text)
                            pim = re.search(r"Штрафное время\s+(\d+)\s+(\d+)", stat_text)
                            
                            t_wh = (int(wh.group(1)) + int(wh.group(2))) if wh else 0
                            t_pim = (int(pim.group(1)) + int(pim.group(2))) if pim else 0
                            
                            print(f"      📊 Стата: Бр={t_sh}, Свист={t_wh}, Штр={t_pim}", flush=True)

                            # Условия сигнала
                            if t_sh >= 13 and t_pim >= 2 and t_wh >= 1:
                                msg = (
                                    f"🚨 <b>СИГНАЛ P1</b>\n"
                                    f"🎯 Броски: {t_sh}\n"
                                    f"❌ Удаления: {t_wh}\n"
                                    f"⏱ Штрафное время: {t_pim}\n"
                                    f"🔗 ID: <code>{m_id}</code>"
                                )
                                await send_tg(msg)
                                TRACKED_MATCHES[m_id] = {
                                    "shots": t_sh,
                                    "penalties": t_wh,
                                    "pim": t_pim,
                                    "notified_at": asyncio.get_event_loop().time()
                                }
                                save_data()
                            else:
                                print(f"      ❌ Условия не выполнены (Бр={t_sh}, Штр={t_pim}, Уд={t_wh})")

                        except Exception as inner_e:
                            print(f"      ⚠️ Ошибка обработки матча {m_id}: {inner_e}")
                        finally:
                            await det.close()

                    except Exception as row_e:
                        print(f"   ⚠️ Ошибка обработки строки: {row_e}")
                        continue

                await asyncio.sleep(45)  # Уменьшили с 60 до 45 для быстроты реакции
                
            except Exception as e:
                print(f"⚠️ Глобальная ошибка: {e}", flush=True)
                await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(main())
