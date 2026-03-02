import asyncio
import aiohttp

def log(msg):
    print(msg, flush=True)

# Наш список лиг (SofaScore пишет их по-английски или по-русски)
WHITE_LIST = ['NHL', 'KHL', 'НХЛ', 'КХЛ', 'AHL', 'Extraliga', 'SHL', 'Liiga']

async def get_sofascore_stats(session, event_id):
    """Тянем броски и штрафы из открытого API SofaScore"""
    url = f"https://api.sofascore.com/api/v1/event/{event_id}/statistics"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0",
        "Origin": "https://www.sofascore.com",
        "Referer": "https://www.sofascore.com/"
    }
    try:
        async with session.get(url, headers=headers, timeout=10) as r:
            if r.status != 200: return 0, 0
            data = await r.json()
            sh, pn = 0, 0
            
            # SofaScore отдает стату в удобных списках
            for period in data.get('statistics', []):
                if period.get('period') == 'ALL': # Берем за весь матч
                    for group in period.get('groups', []):
                        for item in group.get('statisticsItems', []):
                            name = item.get('name', '').lower()
                            # Ищем по английским или русским ключам
                            if 'shots on goal' in name or 'броски в створ' in name:
                                sh = int(item.get('home', 0)) + int(item.get('away', 0))
                            if 'penalty minutes' in name or 'штраф' in name:
                                pn = int(item.get('home', 0)) + int(item.get('away', 0))
            return sh, pn
    except:
        return 0, 0

async def main():
    log("--- 🚀 v132.0: SOFASCORE API (БЕЗ КЛЮЧЕЙ И ВЫЛЕТОВ) ---")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0"
    }
    
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                # 1. Забираем ВСЕ лайв-матчи по хоккею
                live_url = "https://api.sofascore.com/api/v1/sport/ice-hockey/events/live"
                async with session.get(live_url, headers=headers, timeout=10) as r:
                    if r.status == 200:
                        data = await r.json()
                        events = data.get('events', [])
                        
                        found = 0
                        for ev in events:
                            league = ev.get('tournament', {}).get('name', '')
                            
                            # Проверяем, наша ли это лига
                            if not any(l.upper() in league.upper() for l in WHITE_LIST):
                                continue
                                
                            found += 1
                            ev_id = ev.get('id')
                            home = ev.get('homeTeam', {}).get('name', 'Home')
                            away = ev.get('awayTeam', {}).get('name', 'Away')
                            
                            # Статус: Period 1, Pause (Перерыв), Ended и т.д.
                            status = ev.get('status', {}).get('description', 'Live')
                            h_score = ev.get('homeScore', {}).get('current', 0)
                            a_score = ev.get('awayScore', {}).get('current', 0)
                            
                            # 2. Мгновенно тянем стату по ID матча
                            sh, pn = await get_sofascore_stats(session, ev_id)
                            
                            log(f"🏒 [{league}] {home} {h_score}-{a_score} {away} | Статус: {status} | Броски: {sh} | Штраф: {pn}")
                        
                        if found == 0:
                            log("📭 Подходящих матчей НХЛ/КХЛ сейчас нет в лайве.")
                    else:
                        log(f"🛑 Ошибка доступа к лайву: HTTP {r.status}")
                        
            except Exception as e:
                log(f"🛑 Ошибка цикла: {e}")
            
            log("--- Жду 40 сек ---")
            await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())
