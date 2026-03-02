import asyncio
import aiohttp

LEAGUES = ['KHL', 'КХЛ', 'NHL', 'НХЛ', 'AHL', 'АХЛ']

async def get_stats(session, mid):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://www.sofascore.com",
        "Referer": "https://www.sofascore.com/"
    }
    try:
        url = f"https://api.sofascore.com/api/v1/event/{mid}/statistics"
        async with session.get(url, headers=headers, timeout=10) as r:
            if r.status != 200: return 0, 0
            data = await r.json()
            periods = data.get('statistics', [])
            if not periods: return 0, 0

            # Выбираем лучший блок: сначала 'ALL', если нет - последний доступный (1st period и т.д.)
            target = next((p for p in periods if p.get('period') == 'ALL'), periods[0])
            
            sh, pn = 0, 0
            for group in target.get('groups', []):
                for item in group.get('statisticsItems', []):
                    name = item.get('name', '').lower()
                    
                    # Универсальный тягач значений
                    def get_val(side):
                        v = item.get(f'{side}Value') or item.get(side) or '0'
                        return int(str(v).split('(')[0].replace('%','').strip())

                    # БРОСКИ: ищем "shots on goal", "target" или "створ"
                    if any(x in name for x in ['target', 'goal', 'створ', 'shot']) and 'block' not in name:
                        sh = get_val('home') + get_val('away')
                    
                    # ШТРАФ: возвращаем как было в v132
                    if any(x in name for x in ['penalty', 'штраф', 'min']):
                        pn = get_val('home') + get_val('away')
            
            return sh, pn
    except: return 0, 0

async def main():
    print("--- 🔥 v139.0: СТАТИСТИКА ОЖИВАЕТ ---", flush=True)
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
                        status = ev['status']['description']
                        
                        sh, pn = await get_stats(session, mid)
                        print(f"🏒 {home} {score} {away} | {status} | Броски: {sh} | Штраф: {pn}", flush=True)
            except: pass
            await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(main())
