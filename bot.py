import asyncio
import aiohttp

# Твои лиги
LEAGUES = ['KHL', 'КХЛ', 'NHL', 'НХЛ', 'AHL', 'АХЛ']

async def get_stats(session, mid):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://www.sofascore.com",
        "Referer": "https://www.sofascore.com/"
    }
    try:
        url = f"https://api.sofascore.com/api/v1/event/{mid}/statistics"
        async with session.get(url, headers=headers, timeout=5) as r:
            if r.status != 200: return 0, 0
            data = await r.json()
            sh, pn = 0, 0
            
            for p in data.get('statistics', []):
                if p.get('period') == 'ALL':
                    for g in p.get('groups', []):
                        for i in g.get('statisticsItems', []):
                            name = i.get('name', '').lower()
                            
                            # Универсальный тягач цифр
                            def val(side):
                                v = i.get(f'{side}Value') or i.get(side) or '0'
                                return int(str(v).split('(')[0].replace('%','').strip())

                            if any(x in name for x in ['shots on goal', 'shots on target', 'удары в створ']):
                                sh = val('home') + val('away')
                            if 'penalty' in name or 'штраф' in name:
                                pn = val('home') + val('away')
            return sh, pn
    except: return 0, 0

async def main():
    print("--- 🚀 v137.0: ЧИСТЫЙ ХОККЕЙ ---", flush=True)
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
                        home = ev['homeTeam']['shortName']
                        away = ev['awayTeam']['shortName']
                        score = f"{ev['homeScore'].get('current',0)}-{ev['awayScore'].get('current',0)}"
                        status = ev['status']['description']
                        
                        sh, pn = await get_stats(session, mid)
                        print(f"🏒 {home} {score} {away} | {status} | Броски: {sh} | Штраф: {pn}", flush=True)
            except: pass
            await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())
