import asyncio, aiohttp, os

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
SENT_SIGNALS = set()

async def main():
    print("--- 🛠 v178.0: АНАЛИЗАТОР ОШИБОК ЗАПУЩЕН ---", flush=True)
    
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        while True:
            try:
                async with session.get("https://api.sofascore.com/api/v1/sport/ice-hockey/events/live", timeout=10) as r:
                    if r.status != 200: continue
                    events = (await r.json()).get('events', [])
                    print(f"🔎 Сканирую матчей: {len(events)}", flush=True)

                for ev in events:
                    try:
                        mid = ev.get('id')
                        # Защита от кривых данных:
                        home_team = ev.get('homeTeam', {})
                        away_team = ev.get('awayTeam', {})
                        h_name = home_team.get('name', home_team.get('shortName', 'Unknown'))
                        a_name = away_team.get('name', away_team.get('shortName', 'Unknown'))
                        
                        status = ev.get('status', {}).get('code', 0)
                        
                        print(f"📋 {h_name} - {a_name} | Status: {status}", flush=True)

                        if status == 31:
                            print(f"🎯 ПЕРЕРЫВ: {h_name}. Иду за статой...", flush=True)
                            
                            async with session.get(f"https://api.sofascore.com/api/v1/event/{mid}/statistics") as rs:
                                if rs.status == 200:
                                    st_data = await rs.json()
                                    p1 = next((p for p in st_data.get('statistics', []) if p.get('period') == '1ST'), None)
                                    
                                    if p1:
                                        s = {i['key']: int(i.get('homeValue',0)) + int(i.get('awayValue',0)) 
                                             for g in p1.get('groups', []) for i in g.get('statisticsItems', [])}
                                        
                                        on_g = s.get('shotsOnGoal', 0)
                                        pens = s.get('penaltyMinutes', 0)
                                        h_p1 = ev.get('homeScore', {}).get('period1', 0)
                                        a_p1 = ev.get('awayScore', {}).get('period1', 0)

                                        print(f"📊 {h_name}: Счёт {h_p1}:{a_p1}, Броски: {on_g}, Штраф: {pens}", flush=True)

                                        if mid not in SENT_SIGNALS and (h_p1 + a_p1) <= 1 and on_g >= 13 and pens >= 2:
                                            msg = (f"🏒 <b>СИГНАЛ: {h_name} — {a_name}</b>\n"
                                                   f"🥅 Счет P1: {h_p1}:{a_p1}\n🎯 Броски: {on_g}\n⏳ Штраф: {pens}м")
                                            await session.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                                             json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})
                                            SENT_SIGNALS.add(mid)
                                            print(f"✅ СИГНАЛ ОТПРАВЛЕН!", flush=True)
                    except Exception as match_e:
                        print(f"⚠️ Ошибка в матче {mid}: {match_e}", flush=True)

            except Exception as e:
                print(f"🆘 Ошибка цикла: {e}", flush=True)
            
            await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(main())
