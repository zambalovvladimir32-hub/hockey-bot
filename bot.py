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

            # 1. Приоритет блоку 'ALL', если нет - текущему периоду
            target = next((p for p in periods if p.get('period') == 'ALL'), periods[0])
            
            sh, pn = 0, 0
            for group in target.get('groups', []):
                for item in group.get('statisticsItems', []):
                    # Используем системный 'key' — он надежнее названия
                    stat_key = str(item.get('key', '')).lower()
                    stat_name = str(item.get('name', '')).lower()
                    
                    def extract(side):
                        # Ищем значение в разных полях (Value, Total или просто side)
                        val = item.get(f'{side}Value') or item.get(f'{side}Total') or item.get(side) or '0'
                        try:
                            # Убираем всё лишнее: скобки, проценты, дроби (для КХЛ)
                            return int(str(val).split('(')[0].split('/')[0].replace('%','').strip())
                        except: return 0

                    # 🏒 УДАРЫ В СТВОР (Только shotsOnGoal или Shots on target)
                    is_on_goal = 'shotsongoal' in stat_key or 'shotsontarget' in stat_key or \
                                 ('створ' in stat_name)
                    
                    if is_on_goal:
                        sh = extract('home') + extract('away')
                    
                    # ⏳ ШТРАФНОЕ ВРЕМЯ (Penalty minutes)
                    is_penalty = 'penaltyminutes' in stat_key or 'штраф' in stat_name or 'penalty' in stat_name
                    if is_penalty:
                        pn = extract('home') + extract('away')
            
            return sh, pn
    except: return 0, 0
