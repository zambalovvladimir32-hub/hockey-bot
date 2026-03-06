import asyncio
import os
import re
import json
from playwright.async_api import async_playwright

# --- КОНФИГ ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")

API_DOMAIN = None
API_HEADERS = None
FEED_URL = None

BLACKLIST_FILE = "blacklist.json"
WHITELIST_FILE = "whitelist.json"

def load_list(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_list(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(list(data), f, ensure_ascii=False, indent=4)

BLACKLIST = load_list(BLACKLIST_FILE)
WHITELIST = load_list(WHITELIST_FILE)

async def send_tg(text):
    import aiohttp
    if not TOKEN or not CHAT_ID: return
    async with aiohttp.ClientSession() as session:
        try: await session.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
        except: pass

async def send_tg_chunked(text):
    # Телеграм не пропускает сообщения длиннее 4096 символов, поэтому режем на куски
    for i in range(0, len(text), 4000):
        await send_tg(text[i:i+4000])

async def main():
    print("--- 🧠 БОТ-АРХИВАРИУС: МАШИНА ВРЕМЕНИ (7 ДНЕЙ) ---", flush=True)
    global API_DOMAIN, API_HEADERS, FEED_URL, BLACKLIST, WHITELIST
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()

        async def handle_request(request):
            global API_DOMAIN, API_HEADERS, FEED_URL
            if "flashscore.ninja" in request.url and "x-fsign" in request.headers:
                # Ловим фиды дней (f_4 или r_4 для архивов), игнорируем запросы статистики (df_st)
                if ("feed/f_4" in request.url or "feed/r_4" in request.url) and "df_st" not in request.url:
                    FEED_URL = request.url
                    match = re.search(r"(https://[a-zA-Z0-9.-]+\.flashscore\.ninja)", request.url)
                    if match: API_DOMAIN = match.group(1)
                    
                    API_HEADERS = {
                        "x-fsign": request.headers["x-fsign"],
                        "X-Requested-With": "XMLHttpRequest",
                        "Referer": "https://www.flashscore.com/",
                        "Cache-Control": "no-cache"
                    }

        page.on("request", handle_request)

        # Проходим от сегодня (0) до 7 дней назад
        for day in range(8):
            FEED_URL = None # Сбрасываем URL для нового дня
            
            day_label = "СЕГОДНЯ" if day == 0 else f"{day} ДНЕЙ НАЗАД"
            print(f"\n⏳ ПРЫЖОК ВО ВРЕМЕНИ: {day_label} (d=-{day})", flush=True)
            
            await page.goto(f"https://www.flashscore.com/hockey/?d=-{day}", timeout=40000)
            
            for _ in range(15):
                if FEED_URL: break
                await asyncio.sleep(1)

            if not FEED_URL:
                print(f"❌ Не удалось поймать фид для дня -{day}. Пропускаю...", flush=True)
                continue

            print(f"✅ База поймана: {FEED_URL.split('/')[-1]}. Начинаю сканирование...", flush=True)

            response = await context.request.get(FEED_URL, headers=API_HEADERS)
            text = await response.text()
            
            blocks = text.split("~")
            current_league = "Unknown League"
            
            for block in blocks:
                if block.startswith("ZA÷"):
                    league_match = re.search(r"ZA÷([^¬]+)", block)
                    if league_match:
                        current_league = league_match.group(1).strip()
                    continue
                    
                if block.startswith("AA÷"):
                    # Ищем ТОЛЬКО завершенные матчи (статусы 3, 8, 9)
                    if not re.search(r"¬AC÷[389]¬", block): continue 
                    
                    # Если лига уже проверена - пропускаем моментально
                    if current_league in BLACKLIST or current_league in WHITELIST:
                        continue

                    m_id = block.split("¬")[0].replace("AA÷", "")
                    print(f"   🔍 Изучаю новую лигу: 🏆 {current_league}", flush=True)

                    stat_url = f"{API_DOMAIN}/2/x/feed/df_st_1_{m_id}"
                    try:
                        stat_response = await context.request.get(stat_url, headers=API_HEADERS)
                        stat_data = await stat_response.text()

                        if not stat_data or "SG÷" not in stat_data:
                            print(f"      🗑 Пусто. '{current_league}' -> ЧЕРНЫЙ СПИСОК", flush=True)
                            BLACKLIST.add(current_league)
                            save_list(BLACKLIST_FILE, BLACKLIST)
                            continue

                        p1_data = None
                        if "~SE÷" in stat_data:
                            for tab in stat_data.split("~SE÷"):
                                if re.search(r"^(1st Period|1-й период|1\. Period|Period 1)", tab, re.IGNORECASE):
                                    p1_data = tab
                                    break
                        
                        if not p1_data:
                            p1_data = stat_data

                        sh = re.search(r"SG÷(?:Shots on Goal|Броски в створ)¬SH÷(\d+)¬SI÷(\d+)", p1_data, re.IGNORECASE)

                        if sh:
                            print(f"      ✅ Броски есть! '{current_league}' -> БЕЛЫЙ СПИСОК", flush=True)
                            WHITELIST.add(current_league)
                            save_list(WHITELIST_FILE, WHITELIST)
                        else:
                            print(f"      🗑 Бросков в P1 нет. '{current_league}' -> ЧЕРНЫЙ СПИСОК", flush=True)
                            BLACKLIST.add(current_league)
                            save_list(BLACKLIST_FILE, BLACKLIST)
                            
                    except Exception as e:
                        print(f"      ⚠️ Ошибка проверки статы: {e}", flush=True)
                        
                    await asyncio.sleep(0.3) # Анти-бан пауза

        print(f"\n🏁 ПУТЕШЕСТВИЕ ВО ВРЕМЕНИ ЗАВЕРШЕНО!")
        print(f"📊 Итоговые знания: {len(WHITELIST)} хороших лиг, {len(BLACKLIST)} мусорных.")
        print("📨 Отправляю отчет в Telegram...", flush=True)

        # Формируем красивое сообщение для Telegram
        if WHITELIST:
            sorted_whitelist = sorted(list(WHITELIST))
            tg_msg = f"🏆 <b>БЕЛЫЙ СПИСОК ЛИГ ({len(WHITELIST)} шт.)</b>\n<i>Собрано за 7 дней:</i>\n\n"
            for league in sorted_whitelist:
                tg_msg += f"✅ {league}\n"
            
            await send_tg_chunked(tg_msg)
            print("✅ Отчет успешно отправлен в TG!", flush=True)
        else:
            await send_tg("🤷‍♂️ За 7 дней не найдено ни одной лиги с бросками (что-то пошло не так).")
            print("⚠️ Белый список пуст.", flush=True)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
