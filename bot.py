import asyncio
import os
import json
import re
from playwright.async_api import async_playwright

# --- КОНФИГ ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
DB_MATCHES = "tracked_matches.json"
WHITE_LIST = "whitelist_leagues.json"
GREY_LIST = "greylist_leagues.json"
BLACK_LIST = "blacklist_leagues.json"

TRACKED = {}
WHITELIST = set()
GREYLIST = set()
BLACKLIST = set()

def load_data():
    global TRACKED, WHITELIST, GREYLIST, BLACKLIST
    try:
        if os.path.exists(DB_MATCHES): TRACKED = json.load(open(DB_MATCHES, 'r'))
        if os.path.exists(WHITE_LIST): WHITELIST = set(json.load(open(WHITE_LIST, 'r')))
        if os.path.exists(GREY_LIST): GREYLIST = set(json.load(open(GREY_LIST, 'r')))
        if os.path.exists(BLACK_LIST): BLACKLIST = set(json.load(open(BLACK_LIST, 'r')))
    except Exception as e:
        print(f"⚠️ Ошибка загрузки баз: {e}")

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(list(data) if isinstance(data, set) else data, f, ensure_ascii=False)

async def send_tg(text):
    if not TOKEN or not CHAT_ID: return
    import aiohttp
    async with aiohttp.ClientSession() as session:
        try: 
            await session.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                               json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
        except: pass

async def main():
    print(f"--- 🦾 БОТ V60: ГИБКИЙ СЕРЫЙ СПИСОК ---", flush=True)
    load_data()
    print(f"📂 Базы: Белый({len(WHITELIST)}), Серый({len(GREYLIST)}), Черный({len(BLACKLIST)})", flush=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()
        await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "font", "media"] else route.continue_())

        while True:
            try:
                print(f"\n📡 Сканирую Flashscore (Live)...", flush=True)
                await page.goto("https://www.flashscore.com/hockey/?s=2", timeout=40000, wait_until="domcontentloaded")
                await page.wait_for_selector(".event__match", timeout=15000)

                rows = await page.locator(".event__match").all()
                for row in rows:
                    try:
                        m_id = (await row.get_attribute("id")).split("_")[-1]
                        if m_id in TRACKED: continue

                        stage = (await row.locator(".event__stage").inner_text()).lower()
                        if not any(x in stage for x in ["break", "перерыв", "1st"]): continue
                        if any(x in stage for x in ["2nd", "3rd", "2-й", "3-й"]): continue

                        sc_h = await row.locator(".event__score--home").inner_text()
                        sc_a = await row.locator(".event__score--away").inner_text()
                        if not (sc_h.isdigit() and sc_a.isdigit()): continue
                        if (int(sc_h) + int(sc_a)) > 1: continue

                        home = await row.locator(".event__participant--home").inner_text()
                        away = await row.locator(".event__participant--away").inner_text()

                        det = await context.new_page()
                        try:
                            await det.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/0", timeout=25000)
                            
                            try:
                                league = (await det.locator(".breadcrumb__item").last().inner_text()).strip()
                            except:
                                league = "Unknown League"

                            # ЖЕСТКИЙ БЛОК: Только для Черного списка (вообще нет статы)
                            if league in BLACKLIST:
                                print(f"   🚫 {league} в ЧС. Пропускаю.", flush=True)
                                continue

                            # Если лига в Сером списке, мы сообщаем, что заходим проверить её снова
                            if league in GREYLIST:
                                print(f"   🔘 ПЕРЕРЫВ: {home} - {away} | Лига: {league} (Проверяю Серый список...)", flush=True)
                            else:
                                print(f"   🎯 ПЕРЕРЫВ: {home} - {away} | Лига: {league}", flush=True)

                            tabs = await det.locator(".tabs__tab").all_inner_texts()
                            has_stats_tab = any("Stat" in t or "Стат" in t for t in tabs)

                            if not has_stats_tab:
                                print(f"   ⚫ НЕТ ВЗРОСЛОЙ СТАТИСТИКИ. {league} -> ЧЕРНЫЙ СПИСОК", flush=True)
                                BLACKLIST.add(league)
                                save_json(BLACK_LIST, BLACKLIST)
                                # Если вдруг она была в других списках, удаляем
                                if league in GREYLIST:
                                    GREYLIST.discard(league)
                                    save_json(GREY_LIST, GREYLIST)
                                if league in WHITELIST:
                                    WHITELIST.discard(league)
                                    save_json(WHITE_LIST, WHITELIST)
                                continue

                            try:
                                await det.wait_for_selector(".stat__row", timeout=7000)
                                content = await det.evaluate("document.body.innerText")
                                
                                sh_match = re.search(r"(\d+)[\s\n]+(?:Shots on Goal|Броски в створ)[\s\n]+(\d+)", content, re.I)
                                
                                if sh_match:
                                    # ПОВЫШЕНИЕ СТАТУСА: Если броски нашлись, переводим лигу в Белый список!
                                    if league in GREYLIST:
                                        GREYLIST.discard(league)
                                        save_json(GREY_LIST, GREYLIST)
                                        print(f"   ⬆️ АПГРЕЙД! Броски появились. {league} переведена из Серого в БЕЛЫЙ СПИСОК!", flush=True)
                                        
                                    if league not in WHITELIST:
                                        WHITELIST.add(league)
                                        save_json(WHITE_LIST, WHITELIST)
                                        if league not in GREYLIST: # Чтобы не дублировать лог апгрейда
                                            print(f"   ⚪ Отличная лига! {league} -> БЕЛЫЙ СПИСОК", flush=True)
                                    
                                    wh_match = re.search(r"(\d+)[\s\n]+(?:Penalties|Удаления)[\s\n]+(\d+)", content, re.I)
                                    pim_match = re.search(r"(\d+)[\s\n]+(?:PIM|Штрафное время)[\s\n]+(\d+)", content, re.I)

                                    t_sh = int(sh_match.group(1)) + int(sh_match.group(2))
                                    t_wh = (int(wh_match.group(1)) + int(wh_match.group(2))) if wh_match else 0
                                    t_pim = (int(pim_match.group(1)) + int(pim_match.group(2))) if pim_match else 0

                                    print(f"      📈 СТАТА: Бр={t_sh}, Удал={t_wh}, Штраф={t_pim}", flush=True)

                                    if t_sh >= 13 and t_pim >= 2 and t_wh >= 1:
                                        msg = (f"🚨 <b>СИГНАЛ P1</b>\n"
                                               f"🏆 Лига: {league}\n"
                                               f"🤝 {home} — {away} ({sc_h}:{sc_a})\n"
                                               f"🎯 Броски: {t_sh} | ❌ Удаления: {t_wh} | ⏳ Штраф: {t_pim} мин\n"
                                               f"🔗 <a href='https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/0'>Открыть матч</a>")
                                        await send_tg(msg)
                                        print(f"      ✅ СИГНАЛ ОТПРАВЛЕН В ТЕЛЕГРАМ!", flush=True)
                                        
                                        TRACKED[m_id] = True
                                        save_json(DB_MATCHES, TRACKED)
                                    else:
                                        print(f"      ⚠️ Не дотянули до критериев.", flush=True)
                                else:
                                    # Если бросков так и нет, просто оставляем в Сером списке
                                    if league not in GREYLIST:
                                        GREYLIST.add(league)
                                        save_json(GREY_LIST, GREYLIST)
                                        print(f"   🔘 Бросков нет. {league} -> СЕРЫЙ СПИСОК", flush=True)
                                    else:
                                        print(f"   🔘 Бросков пока нет. Оставляю в Сером списке.", flush=True)
                            except:
                                print(f"   ⚠️ Статистика не прогрузилась. Пропущу пока.", flush=True)
                        finally:
                            await det.close()
                    except: continue

                print("💤 Цикл окончен. Сплю 60 секунд...", flush=True)
                await asyncio.sleep(60)
            except Exception as e:
                print(f"⚠️ Глобальная ошибка цикла: {e}", flush=True)
                await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(main())
