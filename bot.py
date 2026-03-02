async def get_stats(session, mid):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://www.sofascore.com",
        "Referer": "https://www.sofascore.com/"
    }
    try:
        url = f"https://api.sofascore.com/api/v1/event/{mid}/statistics"
        async with session.get(url, headers=headers, timeout=7) as r:
            if r.status != 200: return 0, 0
            data = await r.json()
            stats_list = data.get('statistics', [])
            if not stats_list: return 0, 0
            
            # 1. Сначала ищем блок 'ALL'. Если его нет - берем самый первый доступный блок
            target_block = next((p for p in stats_list if p.get('period') == 'ALL'), stats_list[0])
            
            sh, pn = 0, 0
            for group in target_block.get('groups', []):
                for item in group.get('statisticsItems', []):
                    name = item.get('name', '').lower()
                    
                    # Функция вытягивания цифр (теперь еще надежнее)
                    def extract(side):
                        # Проверяем все возможные ключи SofaScore
                        val = item.get(f'{side}Value') or item.get(side) or item.get(f'{side}Total') or '0'
                        try:
                            return int(str(val).split('(')[0].replace('%','').strip())
                        except: return 0

                    # 🏒 БРОСКИ (Shots on goal / Shots on target / Броски)
                    if any(x in name for x in ['shot', 'target', 'створ', 'броски']):
                        # Исключаем 'blocked shots' (блокированные), нам нужны только в створ
                        if 'block' not in name:
                            sh = extract('home') + extract('away')
                    
                    # ⏳ ШТРАФ (Penalty minutes / Suspensions / Штраф)
                    if any(x in name for x in ['penalty', 'штраф', 'suspension', 'мин']):
                        pn = extract('home') + extract('away')
            
            return sh, pn
    except Exception as e:
        return 0, 0
