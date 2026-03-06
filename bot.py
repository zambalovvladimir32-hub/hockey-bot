import asyncio
import os
import re
from curl_cffi.requests import AsyncSession

# --- КОНФИГ ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
# Если есть прокси, пиши сюжа. Если нет, оставь пустым ""
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
    """Обход Cloudflare через эмуляцию Chrome 120"""
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
    try:
        # impersonate="chrome120" - вот она, магия обхода Cloudflare!
        response = await session.get(url, headers=headers, proxies=proxies, impersonate="chrome120", timeout=15)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        print(f"📡 Ошибка соединения: {e}")
    return None

async def main():
    print(f"--- ☢️ БОТ V99: GHOST PROTOCOL (CURL_CFFI) ---", flush=True)
    
    # Секретные заголовки, которые использует мобильное приложение Flashscore
    headers = {
        "x-fsign": "SW9D1eZo", # Ключ дешифратора фидов
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.flashscore.com/"
    }

    # Инициализируем сессию-невидимку
    async with AsyncSession() as session:
        while True:
            try:
                print("\n📡 Взламываю Live-фид...", flush=True)
                # f_4_1_2_ru_1: 4 - хоккей, 1 - live, ru - язык
                live_feed_url = "https://d.flashscore.com/x/feed/f_4_1_2_ru_1"
                
                feed_data = await fetch_api(session, live_feed_url, headers)
                
                if not feed_data or "~AA÷" not in feed_data:
                    print("❌ Блок от Cloudflare или нет лайв матчей. Жду...", flush=True)
                    await asyncio.sleep(30)
                    continue

                # Flashscore шлет данные странной строкой, режем ее на матчи
                matches = feed_data.split("~AA÷")
                print(f"📊 Скачано сырых событий: {len(matches)-1}", flush=True)

                for match_data in matches[1:]:
                    try:
                        # Парсим сырую строку
                        m_id = match_data.split("¬")[0]
                        
                        # Ищем текущий статус матча (36 - это код перерыва P1)
                        if "¬AC÷36¬" not in match_data: continue
                        
                        if m_id in TRACKED_MATCHES: continue

                        # Ищем названия команд (AE - Home, AF - Away)
                        home_match = re.search(r"AE÷([^¬]+)", match_data)
                        away_match = re.search(r"AF÷([^¬]+)", match_data)
                        home = home_match.group(1) if home_match else "Home"
                        away = away_match.group(1) if away_match else "Away"

                        # Ищем счет (AG - Home Score, AH - Away Score)
                        sc_h_match = re.search(r"AG÷(\d+)", match_data)
                        sc_a_match = re.search(r"AH÷(\d+)", match_data)
                        sc_h = int(sc_h_match.group(1)) if sc_h_match else 0
                        sc_a = int(sc_a_match.group(1)) if sc_a_match else 0

                        if (sc_h + sc_a) > 1: continue # Фильтр тотала

                        print(f"   🎯 ПЕРЕРЫВ: {home} - {away} ({sc_h}:{sc_a}). Качаю статку...", flush=True)

                        # Запрашиваем статистику напрямую через API
                        stat_url = f"https://d.flashscore.com/x/feed/df_st_1_{m_id}"
                        stat_data = await fetch_api(session, stat_url, headers)

                        if stat_data:
                            # Парсим броски в створ (на английском Shots on Goal)
                            # SG÷ - код параметра, SH÷ - Home, SI÷ - Away
                            # Пример: SG÷Shots on Goal¬SH÷10¬SI÷5
                            sh_match = re.search(r"SG÷(?:Shots on Goal|Броски в створ)¬SH÷(\d+)¬SI÷(\d+)", stat_data)
                            wh_match = re.search(r"SG÷(?:Penalties|Удаления)¬SH÷(\d+)¬SI÷(\d+)", stat_data)
                            pim_match = re.search(r"SG÷(?:PIM|Штрафное время)¬SH÷(\d+)¬SI÷(\d+)", stat_data)

                            if sh_match:
                                t_sh = int(sh_match.group(1)) + int(sh_match.group(2))
                                t_wh = int(wh_match.group(1)) + int(wh_match.group(2)) if wh_match else 0
                                t_pim = int(pim_match.group(1)) + int(pim_match.group(2)) if pim_match else 0

                                print(f"      📈 СТАТА (API): Бр={t_sh}, Удал={t_wh}, Штраф={t_pim}", flush=True)

                                if t_sh >= 13 and t_pim >= 2 and t_wh >= 1:
                                    msg = (f"🚨 <b>СИГНАЛ P1 (DIRECT API)</b>\n"
                                           f"🤝 {home} — {away} ({sc_h}:{sc_a})\n"
                                           f"🎯 Броски: {t_sh} | ❌ Удаления: {t_wh} | ⏳ Штраф: {t_pim} мин\n"
                                           f"🔗 <a href='https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/0'>Открыть матч</a>")
                                    await send_tg(msg)
                                    TRACKED_MATCHES.add(m_id)
                                    print("      ✅ СИГНАЛ В КАНАЛЕ!", flush=True)
                                else:
                                    print("      ⚠️ Не подошло по критериям.", flush=True)
                            else:
                                print("      🧐 В API нет данных по броскам для этого матча.", flush=True)
                        else:
                            print("      ❌ Не удалось загрузить API статистики.", flush=True)

                    except Exception as e:
                        print(f"   ⚠️ Ошибка парсинга матча: {e}", flush=True)

                await asyncio.sleep(60)
            except Exception as e:
                print(f"⚠️ Глобальная ошибка: {e}", flush=True)
                await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(main())
