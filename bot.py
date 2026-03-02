import asyncio
import aiohttp

LEAGUES = ['KHL', 'КХЛ', 'NHL', 'НХЛ', 'AHL', 'АХЛ']

async def get_stats(session, mid):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        url = f"https://api.sofascore.com/api/v1/event/{mid}/statistics"
        async with session.get(url, headers=headers, timeout=10) as r:
            if r.status != 200: return 0, 0, "API_ERROR"
            data = await r.json()
            periods = data.get('statistics', [])
            if not periods: return 0, 0, "EMPTY_STATS"

            target = next((p for p in periods if p.get('period') == 'ALL'), periods[0])
            
            sh_on_goal = 0
            penalty_min = 0
            found_names = [] # Собираем все названия, чтобы увидеть их глазами
            
            for group in target.get('groups', []):
                for item in group.get('statisticsItems', []):
                    name = str(item.get('name', ''))
                    found_names.append(name) # Записываем, что нашли
                    
                    name_lower = name.lower()
                    key_lower = str(item.get('key', '')).lower()

                    # Жесткая очистка цифр
                    raw_h = str(item.get('homeValue', item.get('home', '0')))
                    raw_a = str(item.get('awayValue', item.get('away', '0')))
                    h_clean = raw_h.split('(')[0].split('/')[0].replace('%','').strip()
                    a_clean = raw_a.split('(')[0].split('/')[0].replace('%','').strip()
                    
                    try:
                        h_int = int(h_clean)
                        a_int = int(a_clean)
                    except:
                        continue

                    # Ищем УДАРЫ В СТВОР
                    if 'створ' in name_lower or 'shots on goal' in name_lower or 'shots on target' in name_lower or 'shotsongoal' in key_lower:
                        sh_on_goal = h_int + a_int
                    
                    # Ищем ШТРАФ
                    if 'штраф' in name_lower or 'penalty' in name_lower or 'penaltyminutes' in key_lower:
                        penalty_min = h_int + a_int
            
            # Выводим первые 6-7 параметров из JSON, чтобы понять, что там лежит
            debug_info = " | ".join(found_names[:7])
            return sh_on_goal, penalty_min, debug_info
    except Exception as e:
        return 0, 0, str(e)

async def main():
    print("--- 🛠 v143.0: РЕЖИМ РЕНТГЕНА ---", flush=True)
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get("https://api.sofascore.com/api/v1/sport/ice-hockey/events/live", timeout=10) as r:
                    if r.status != 200: continue
                    events = (await r.json()).get('events', [])
                    for ev in events:
                        l_name = ev.get('tournament', {}).get('name', '')
                        if not any(t in l_name.upper() for t in LEAGUES): continue
                        
                        mid = ev.get('id')
                        home, away = ev['homeTeam']['shortName'], ev['awayTeam']['shortName']
                        score = f"{ev['homeScore'].get('current',0)}-{ev['awayScore'].get('current',0)}"
                        
                        sh, pn, dbg = await get_stats(session, mid)
                        
                        print(f"🏒 {home} {score} {away} | Створ: {sh} | Штраф: {pn}", flush=True)
                        print(f"🔍 В JSON прилетело: {dbg}", flush=True)
                        print("-" * 30, flush=True)
            except: pass
            await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())
