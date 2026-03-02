import asyncio
import aiohttp

LEAGUES = ['KHL', 'КХЛ', 'NHL', 'НХЛ', 'AHL', 'АХЛ']

async def get_stats(session, mid):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        url = f"https://api.sofascore.com/api/v1/event/{mid}/statistics"
        async with session.get(url, headers=headers, timeout=10) as r:
            if r.status != 200: return 0, 0
            data = await r.json()
            periods = data.get('statistics', [])
            if not periods: return 0, 0

            target = next((p for p in periods if p.get('period') == 'ALL'), periods[0])
            
            sh_on_goal = 0
            penalty_min = 0
            
            for group in target.get('groups', []):
                for item in group.get('statisticsItems', []):
                    name = str(item.get('name', '')).lower()
                    key = str(item.get('key', '')).lower()

                    raw_h = str(item.get('homeValue', item.get('home', '0')))
                    raw_a = str(item.get('awayValue', item.get('away', '0')))
                    
                    try:
                        h_int = int(raw_h.split('(')[0].split('/')[0].replace('%','').strip())
                        a_int = int(raw_a.split('(')[0].split('/')[0].replace('%','').strip())
                    except: continue

                    # 🎯 ВОТ ОНО! Добавили точный перехват слова 'shots'
                    if name == 'shots' or key == 'shots' or 'створ' in name or 'shotsongoal' in key:
                        sh_on_goal = h_int + a_int
                    
                    # ⏳ ШТРАФ
                    if 'штраф' in name or 'penalty' in name or 'penaltyminutes' in key:
                        penalty_min = h_int + a_int
            
            return sh_on_goal, penalty_min
    except: return 0, 0

async def main():
    print("--- 🎯 v144.0: ФИНАЛЬНЫЙ ЗАХВАТ ---", flush=True)
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
                        
                        sh, pn = await get_stats(session, mid)
                        print(f"🏒 {home} {score} {away} | Створ: {sh} | Штраф: {pn}", flush=True)
            except: pass
            await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())
