import asyncio, aiohttp, os

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
SENT_SIGNALS = set()

async def main():
    print("--- 🔥 v176.0: РЕЖИМ ПОЛНОГО СКАНЕРА ЗАПУЩЕН ---", flush=True)
    
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        while True:
            try:
                # 1. Проверка списка матчей
                async with session.get("https://api.sofascore.com/api/v1/sport/ice-hockey/events/live", timeout=10) as r:
                    if r.status != 200:
                        print(f"❌ Ошибка API SofaScore: {r.status}", flush=True)
                        continue
                    
                    data = await r.json()
                    events = data.get('events', [])
                    
                    if not events:
                        print("📭 В лайве сейчас 0 матчей по хоккею.", flush=True)
                    else:
                        print(f"🔎 Сканирую матчей: {len(events)}", flush=True)

                for ev in events:
                    mid = ev.get('id')
                    home = ev['homeTeam']['shortName']
                    away = ev['awayTeam']['shortName']
                    status = ev.get('status', {}).get('code', 0)
                    
                    # Вывод в логи для каждого матча
                    print(f"📋 [{home}-{away}] ID: {mid} | Status: {status}", flush=True)

                    # Проверяем только перерыв (31)
                    if status == 31:
                        print(f"⏳ МАТЧ В ПЕРЕРЫВЕ: {home}-{away}. Запрашиваю статистику...", flush=True)
                        
                        async with session.get(f"https://api.sofascore.com/api/v1/event/{mid}/statistics") as rs:
                            if rs.status == 200:
                                st = await rs.json()
                                p1 = next((p for p in st.get('statistics', []) if p.get('period') == '1ST'), None)
                                
                                if p1:
                                    stats = {i['key']: int(i.get('homeValue',0)) + int(i.get('awayValue',0)) 
                                             for g in p1.get('groups', []) for i in g.get('statisticsItems', [])}
                                    
                                    shots = stats.get('shotsOnGoal', 0)
                                    pens = stats.get('penaltyMinutes', 0)
                                    
                                    print(f"📊 СТАТА {home}: Броски: {shots}, Штраф: {pens}", flush=True)

                                    # ПРОВЕРКА НАШЕГО АЛГОРИТМА
                                    h_p1 = ev.get('homeScore', {}).get('period1', 0)
                                    a_p1 = ev.get('awayScore', {}).get('period1', 0)

                                    if mid not in SENT_SIGNALS and (h_p1 + a_p1) <= 1 and shots >= 13 and pens >= 2:
                                        msg = (f"🚨 <b>АЛГОРИТМ СРАБОТАЛ!</b>\n"
                                               f"🤝 {home} — {away}\n"
                                               f"🥅 Счет P1: {h_p1}:{a_p1}\n"
                                               f"🎯 Броски: {shots}\n"
                                               f"⏳ Штраф: {pens} мин")
                                        
                                        await session.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                                         json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})
                                        SENT_SIGNALS.add(mid)
                                        print(f"✅ СИГНАЛ ОТПРАВЛЕН В ТГ!", flush=True)
                                else:
                                    print(f"⚠️ Статистика за 1-й период для {home} еще не готова.", flush=True)
                            else:
                                print(f"❌ Не смог забрать статику для {mid}", flush=True)

            except Exception as e:
                print(f"🆘 КРИТИЧЕСКАЯ ОШИБКА: {e}", flush=True)
            
            print("--- Конец цикла, жду 10 сек ---", flush=True)
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
