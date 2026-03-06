import asyncio
import os
import re
from playwright.async_api import async_playwright

# --- КОНФИГ ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
TRACKED_MATCHES = set()

FEED_URL = None
FEED_HEADERS = {}

async def send_tg(text):
    import aiohttp
    if not TOKEN or not CHAT_ID: return
    async with aiohttp.ClientSession() as session:
        try: await session.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
        except: pass

async def main():
    print("--- ☢️ БОТ V104: API SNIPER (PLAYWRIGHT NATIVE API) ---", flush=True)
    global FEED_URL, FEED_HEADERS
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()

        # 1. ПЕРЕХВАТЧИК СЕТИ
        async def handle_request(request):
            global FEED_URL, FEED_HEADERS
            # Ловим запрос, которым сам сайт качает хоккейный лайв
            if "d.flashscore.com/x/feed/f_4" in request.url:
                FEED_URL = request.url
                FEED_HEADERS = request.headers
                print(f"   🎯 Перехвачен точный URL базы: {FEED_URL}", flush=True)

        page.on("request", handle_request)

        print("📡 Захожу на сайт, чтобы пройти Cloudflare и поймать куки...", flush=True)
        # Открываем именно вкладку хоккея в лайве
        await page.goto("https://www.flashscore.com/hockey/?s=2", timeout=40000)
        
        # Ждем пару секунд, чтобы скрипты сайта сделали запросы
        for _ in range(10):
            if FEED_URL: break
            await asyncio.sleep(1)

        if not FEED_URL:
            print("❌ Не удалось поймать ссылку. Перезапускаю...", flush=True)
            await browser.close()
            return

        print("✅ Идеально! Начинаю прямые запросы к базе данных...", flush=True)

        # 2. БЕСКОНЕЧНЫЙ ЦИКЛ API (Без рендеринга визуала)
        while True:
            try:
                print("\n📡 Запрашиваю данные...", flush=True)
                # Делаем запрос в базу через сеть самого браузера (куки подтянутся автоматически!)
                response = await context.request.get(FEED_URL, headers=FEED_HEADERS)
                text = await response.text()
                
                if text == "0":
                    print("⚠️ Токен или куки протухли. Обновляю страницу...", flush=True)
                    await page.reload(timeout=30000)
                    await asyncio.sleep(5)
                    continue

                if "~AA÷" not in text:
                    print("🤷‍♂️ Доступ есть, но лайв сейчас абсолютно пуст.", flush=True)
                    await asyncio.sleep(60)
                    continue

                matches = text.split("~AA÷")
                print(f"📊 Скачано событий: {len(matches)-1}", flush=True)

                for match_data in matches[1:]:
                    try:
                        m_id = match_data.split("¬")[0]
                        if "¬AC÷36¬" not in match_data: continue # Код 36 = Перерыв после 1-го периода
                        if m_id in TRACKED_MATCHES: continue

                        # Парсим имена команд и счет из сырого ответа
                        home_match = re.search(r"AE÷([^¬]+)", match_data)
                        away_match = re.search(r"AF÷([^¬]+)", match_data)
                        home = home_match.group(1) if home_match else "Home"
                        away = away_match.group(1) if away_match else "Away"

                        sc_h_match = re.search(r"AG÷(\d+)", match_data)
                        sc_a_match = re.search(r"AH÷(\d+)", match_data)
                        sc_h = int(sc_h_match.group(1)) if sc_h_match else 0
                        sc_a = int(sc_a_match.group(1)) if sc_a_match else 0

                        if (sc_h + sc_a) > 1: continue

                        print(f"   🎯 ПЕРЕРЫВ P1: {home} - {away} ({sc_h}:{sc_a}). Проверяю статку...", flush=True)

                        # Запрашиваем статистику напрямую в обход интерфейса
                        stat_url = f"https://d.flashscore.com/x/feed/df_st_1_{m_id}"
                        stat_response = await context.request.get(stat_url, headers=FEED_HEADERS)
                        stat_data = await stat_response.text()

                        if stat_data and "SG÷" in stat_data:
                            sh = re.search(r"SG÷(?:Shots on Goal|Броски в створ)¬SH÷(\d+)¬SI÷(\d+)", stat_data)
                            wh = re.search(r"SG÷(?:Penalties|Удаления)¬SH÷(\d+)¬SI÷(\d+)", stat_data)
                            pim = re.search(r"SG÷(?:PIM|Штрафное время)¬SH÷(\d+)¬SI÷(\d+)", stat_data)

                            if sh:
                                t_sh = int(sh.group(1)) + int(sh.group(2))
                                t_wh = int(wh.group(1)) + int(wh.group(2)) if wh else 0
                                t_pim = int(pim.group(1)) + int(pim.group(2)) if pim else 0

                                print(f"      📈 СТАТА: Бр={t_sh}, Удал={t_wh}, Штраф={t_pim}", flush=True)

                                if t_sh >= 13 and t_pim >= 2 and t_wh >= 1:
                                    msg = (f"🚨 <b>СИГНАЛ P1 (NATIVE API)</b>\n"
                                           f"🤝 {home} — {away} ({sc_h}:{sc_a})\n"
                                           f"🎯 Броски: {t_sh} | ❌ Удаления: {t_wh} | ⏳ Штраф: {t_pim} мин\n"
                                           f"🔗 <a href='https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/0'>Открыть матч</a>")
                                    await send_tg(msg)
                                    TRACKED_MATCHES.add(m_id)
                                    print("      ✅ СИГНАЛ В КАНАЛЕ!", flush=True)
                                else:
                                    print("      ⚠️ Стата не подходит.", flush=True)
                            else:
                                print("      🧐 Нет бросков в API для этого матча.", flush=True)
                        else:
                            print("      ❌ Статистика еще не загружена в базу.", flush=True)

                    except Exception as e:
                        print(f"   ⚠️ Ошибка матча: {e}", flush=True)

                await asyncio.sleep(60)
            except Exception as e:
                print(f"⚠️ Ошибка цикла: {e}", flush=True)
                await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(main())
