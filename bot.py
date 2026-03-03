import asyncio
import aiohttp
import os

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")

SENT_SIGNALS = set()
PENDING_REPORTS = {}

WHITE_LIST = [
    "1st Liga", "1st Liga Playoffs", "AHL", "Alps Hockey League, Championship Round",
    "Alps Hockey League, Qualification Round, Group B", "Asia League",
    "Auroraliiga, Women, Playoffs", "DEL", "Ekstraliga, Playoffs", "EliteHockey Ligaen",
    "Extraliga", "Hockey Allsvenskan", "HockeyEttan Sodra", "ICE Hockey League",
    "KHL", "Ligue Magnus", "Liiga", "MHL", "Mestis", "Mestis Playoffs", "NHL",
    "National League", "OHL", "PWHL", "SDHL", "SHL", "Swiss League, Playoffs",
    "Tipsport Liga", "U20 Elite, Qualifying Round", "U20 Extraliga Juniorov",
    "U20 Extraliga Junioru, Championship Round", "U20 Extraliga Junioru, Qualification Round",
    "University League", "VHL", "WHL, Women"
]

async def send_tg(session, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        await session.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
    except Exception as e:
        print(f"Ошибка ТГ: {e}")

async def main():
    print("--- 🎯 v184.0: СНАЙПЕР (ТОЛЬКО ТБ 0.5) ЗАПУЩЕН ---", flush=True)
    
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        while True:
            try:
                async with session.get("https://api.sofascore.com/api/v1/sport/ice-hockey/events/live", timeout=10) as r:
                    if r.status != 200: continue
                    events = (await r.json()).get('events', [])

                for ev in events:
                    try:
                        mid = ev.get('id')
                        status = ev.get('status', {}).get('code', 0)
                        
                        # ==========================================
                        # БЛОК 1: ОТЧЕТЫ ПО СИГНАЛАМ
                        # ==========================================
                        if mid in PENDING_REPORTS and status in [32, 3, 33, 4, 5, 100]:
                            h_p2 = ev.get('homeScore', {}).get('period2', 0)
                            a_p2 = ev.get('awayScore', {}).get('period2', 0)
                            p2_goals = h_p2 + a_p2
                            info = PENDING_REPORTS[mid]
                            
                            # Оставили только одну проверку — был ли гол
                            if p2_goals >= 1:
                                result_text = "✅ <b>ЗАШЛО</b>"
                            else:
                                result_text = "❌ <b>МИНУС (Сушняк)</b>"

                            msg = (f"📊 <b>ОТЧЕТ ПО СИГНАЛУ</b>\n"
                                   f"🤝 <b>{info['home']} — {info['away']}</b>\n"
                                   f"━━━━━━━━━━━━━━━━━━\n"
                                   f"🏒 Голов во 2-м периоде: <b>{p2_goals}</b> ({h_p2}:{a_p2})\n"
                                   f"{result_text}")
                            
                            await send_tg(session, msg)
                            print(f"🧾 Отчет отправлен: {info['home']} (Голов во 2-м: {p2_goals})", flush=True)
                            
                            del PENDING_REPORTS[mid]

                        # ==========================================
                        # БЛОК 2: ПОИСК СИГНАЛОВ
                        # ==========================================
                        l_name = ev.get('tournament', {}).get('name', '')
                        if not any(t.upper() in l_name.upper() for t in WHITE_LIST): continue

                        if status == 31 and mid not in SENT_SIGNALS:
                            h_name = ev.get('homeTeam', {}).get('name', 'Unknown')
                            a_name = ev.get('awayTeam', {}).get('name', 'Unknown')
                            
                            h_p1 = ev.get('homeScore', {}).get('period1', 0)
                            a_p1 = ev.get('awayScore', {}).get('period1', 0)

                            if (h_p1 + a_p1) <= 1:
                                async with session.get(f"https://api.sofascore.com/api/v1/event/{mid}/statistics") as rs:
                                    if rs.status == 200:
                                        st_data = await rs.json()
                                        
                                        p1 = None
                                        for p in st_data.get('statistics', []):
                                            p_name = str(p.get('period', '')).lower()
                                            if '1st' in p_name or '1-й' in p_name or p_name == '1':
                                                p1 = p
                                                break
                                        
                                        if p1:
                                            on_g, pens = 0, 0
                                            
                                            for g in p1.get('groups', []):
                                                for i in g.get('statisticsItems', []):
                                                    key_raw = str(i.get('key', '')).lower().replace(' ', '')
                                                    name_raw = str(i.get('name', '')).lower().replace(' ', '')
                                                    val = int(i.get('homeValue', 0)) + int(i.get('awayValue', 0))
                                                    
                                                    if any(x in key_raw or x in name_raw for x in ['shots', 'выстрелы', 'удары']):
                                                        on_g = val
                                                    if any(x in key_raw or x in name_raw for x in ['penalty', 'penalties', 'штраф', 'удалени']):
                                                        pens = val

                                            if on_g >= 12 and pens >= 2:
                                                msg = (f"🚨 <b>АЛГОРИТМ: ИДЕАЛЬНЫЙ МАТЧ</b>\n"
                                                       f"🏆 {l_name}\n"
                                                       f"🤝 <b>{h_name} — {a_name}</b>\n"
                                                       f"━━━━━━━━━━━━━━━━━━\n"
                                                       f"🥅 Счет P1: <b>{h_p1}:{a_p1}</b>\n"
                                                       f"🎯 Броски в створ: <b>{on_g}</b>\n"
                                                       f"⏳ Штрафы: <b>{pens} мин</b>\n"
                                                       f"━━━━━━━━━━━━━━━━━━\n"
                                                       f"💡 <i>Ждем минимум 1 гол во 2-м периоде.</i>")
                                                
                                                await send_tg(session, msg)
                                                SENT_SIGNALS.add(mid)
                                                PENDING_REPORTS[mid] = {'home': h_name, 'away': a_name}
                                                print(f"✅ Сигнал: {h_name} - {a_name}. Взят на контроль!", flush=True)

                    except Exception as match_e:
                        pass 

            except Exception as e:
                pass 
            
            await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(main())
