import asyncio
import os
import re
from playwright.async_api import async_playwright

# --- КОНФИГ ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
TRACKED_MATCHES = set()

API_DOMAIN = None
API_HEADERS = None

async def send_tg(text):
    import aiohttp
    if not TOKEN or not CHAT_ID: return
    async with aiohttp.ClientSession() as session:
        try: await session.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
        except: pass

async def main():
    print("--- ☢️ БОТ V106: NINJA SNIPER ---", flush=True)
    global API_DOMAIN, API_HEADERS
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()

        # 1. ПЕРЕХВАТЧИК СЕТИ
        async def handle_request(request):
            global API_DOMAIN, API_HEADERS
            # Ищем запросы к ниндзя-доменам, в которых есть секретный ключ
            if "flashscore.ninja" in request.url and "x-fsign" in request.headers:
                if not API_DOMAIN:
                    # Вытаскиваем базовый домен (например, https://global.flashscore.ninja)
                    match = re.search(r"(https://[a-zA-Z0-9.-]+\.flashscore\.ninja)", request.url)
                    if match:
                        API_DOMAIN = match.group(1)
                        API_HEADERS = {
                            "x-fsign": request.headers["x-fsign"],
                            "X-Requested-With": "XMLHttpRequest",
                            "Referer": "https://www.flashscore.com/"
                        }
                        print(f"   🥷 Пойман сервер ниндзя: {API_DOMAIN}", flush=True)
                        print(f"   🔑 Украден ключ: {API_HEADERS['x-fsign'][:10]}...", flush=True)

        page.on("request", handle_request)

        print("📡 Захожу на сайт, выслеживаю API...", flush=True)
        await page.goto("https://www.flashscore.com/hockey/?s=2", timeout=40000)
        
        # Ждем поимки данных (даем скриптам 15 секунд на прогрузку)
        for _ in range(15):
            if API_DOMAIN and API_HEADERS: break
            await asyncio.sleep(1)

        if not API_DOMAIN:
            print("❌ Не удалось поймать Ninja API. Перезапускаю...", flush=True)
            await browser.close()
            return

        print("✅ База данных взломана! Начинаю прямые запросы...", flush=True)

        # 2. БЕСКОНЕЧНЫЙ ЦИКЛ API
        while True:
            try:
                print("\n📡 Запрашиваю Live-матчи...", flush=True)
                # Формируем URL лайва для хоккея
                live_url = f"{API_DOMAIN}/2/x/feed/f_4_1_3_ru_1"
                
                response = await context.request.get(live_url, headers=API_HEADERS)
                text = await response.text()
                
                # Если сервер вернул 0, значит ключ устарел
                if text == "0" or not text:
                    print("⚠️ Токен протух. Обновляю страницу...", flush=True)
                    API_DOMAIN = None
                    await page.reload(timeout=30000)
                    await asyncio.sleep(5)
                    continue

                if "~AA÷" not in text:
                    print("🤷‍♂️ Доступ есть, но лайв сейчас пуст.", flush=True)
                    await asyncio.sleep(60)
                    continue

                matches = text.split("~AA÷")
                print(f"📊 Найдено матчей в лайве: {len(matches)-1}", flush=True)

                for match_data in matches[1:]:
                    try:
                        m_id = match_data.split("¬")[0]
                        if "¬AC÷36¬" not in match_data: continue # Код 36 = Перерыв P1
                        if m_id in TRACKED_MATCHES: continue

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

                        # Статистика запрашивается с того же пойманного домена-ниндзя
                        stat_url = f"{API_DOMAIN}/2/x/feed/df_st_1_{m_id}"
                        stat_response = await context.request.get(stat_url, headers=API_HEADERS)
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
                                    msg = (f"🚨 <b>СИГНАЛ P1 (NINJA API)</b>\n"
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
                            print("      ❌ Статистики еще нет в базе.", flush=True)

                    except Exception as e:
                        print(f"   ⚠️ Ошибка матча: {e}", flush=True)

                await asyncio.sleep(60)
            except Exception as e:
                print(f"⚠️ Ошибка цикла: {e}", flush=True)
                await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(main())
