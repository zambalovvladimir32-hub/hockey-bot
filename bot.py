import asyncio
import os
import re
from curl_cffi.requests import AsyncSession

# --- КОНФИГ ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL", "") 
TRACKED_MATCHES = set()

async def send_tg(text):
    if not TOKEN or not CHAT_ID: return
    async with AsyncSession() as s:
        try:
            await s.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                         json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
        except: pass

async def fetch_api(session, url, headers):
    """Прямой запрос с подменой отпечатков браузера"""
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
    try:
        response = await session.get(url, headers=headers, proxies=proxies, impersonate="chrome124", timeout=15)
        
        # САМОЕ ВАЖНОЕ: ВЫВОДИМ ОТВЕТ СЕРВЕРА В ЛОГ
        print(f"   [HTTP {response.status_code}] Ответ сервера: {response.text[:150].replace(chr(10), ' ')}", flush=True)
        
        if response.status_code == 200:
            return response.text
    except Exception as e:
        print(f"📡 Ошибка соединения: {e}", flush=True)
    return None

async def main():
    print(f"--- ☢️ БОТ V100: ДИАГНОСТИКА СЕРВЕРА ---", flush=True)
    
    headers = {
        "x-fsign": "SW9D1eZo",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.flashscore.com/"
    }

    async with AsyncSession() as session:
        while True:
            try:
                print("\n📡 Стучусь в базу Flashscore...", flush=True)
                live_feed_url = "https://d.flashscore.com/x/feed/f_4_1_2_ru_1"
                
                feed_data = await fetch_api(session, live_feed_url, headers)
                
                if not feed_data:
                    print("❌ Сервер закрыл доступ. Жду 30 сек...", flush=True)
                    await asyncio.sleep(30)
                    continue

                if "~AA÷" not in feed_data:
                    print("🤷‍♂️ Доступ открыт, но матчей сейчас нет (или формат поменялся).", flush=True)
                    await asyncio.sleep(30)
                    continue

                matches = feed_data.split("~AA÷")
                print(f"📊 Скачано матчей в лайве: {len(matches)-1}", flush=True)

                for match_data in matches[1:]:
                    try:
                        m_id = match_data.split("¬")[0]
                        if "¬AC÷36¬" not in match_data: continue # 36 - код перерыва
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

                        print(f"   🎯 ПЕРЕРЫВ: {home} - {away} ({sc_h}:{sc_a}). Качаю статку...", flush=True)

                        stat_url = f"https://d.flashscore.com/x/feed/df_st_1_{m_id}"
                        stat_data = await fetch_api(session, stat_url, headers)

                        if stat_data:
                            sh_match = re.search(r"SG÷(?:Shots on Goal|Броски в створ)¬SH÷(\d+)¬SI÷(\d+)", stat_data)
                            wh_match = re.search(r"SG÷(?:Penalties|Удаления)¬SH÷(\d+)¬SI÷(\d+)", stat_data)
                            pim_match = re.search(r"SG÷(?:PIM|Штрафное время)¬SH÷(\d+)¬SI÷(\d+)", stat_data)

                            if sh_match:
                                t_sh = int(sh_match.group(1)) + int(sh_match.group(2))
                                t_wh = int(wh_match.group(1)) + int(wh_match.group(2)) if wh_match else 0
                                t_pim = int(pim_match.group(1)) + int(pim_match.group(2)) if pim_match else 0

                                print(f"      📈 СТАТА: Бр={t_sh}, Удал={t_wh}, Штраф={t_pim}", flush=True)

                                if t_sh >= 13 and t_pim >= 2 and t_wh >= 1:
                                    msg = f"🚨 <b>СИГНАЛ P1 (API)</b>\n🤝 {home} — {away} ({sc_h}:{sc_a})\n🎯 Броски: {t_sh} | ❌ Удаления: {t_wh} | ⏳ Штраф: {t_pim} мин"
                                    await send_tg(msg)
                                    TRACKED_MATCHES.add(m_id)
                                    print("      ✅ СИГНАЛ В КАНАЛЕ!", flush=True)
                                else:
                                    print("      ⚠️ Стата не дотянула до нужной.", flush=True)
                            else:
                                print("      🧐 В API нет бросков для этого матча.", flush=True)

                    except Exception as e:
                        print(f"   ⚠️ Ошибка парсинга матча: {e}", flush=True)

                await asyncio.sleep(60)
            except Exception as e:
                print(f"⚠️ Ошибка цикла: {e}", flush=True)
                await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(main())
