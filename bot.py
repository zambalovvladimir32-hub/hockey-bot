async def get_stats_with_curl(session, mid):
    try:
        # Тянем ОБЩИЙ фид матча (df_st_0), он самый стабильный
        url = f"https://www.flashscore.ru/x/feed/df_st_0_{mid}"
        headers = {
            "x-fsign": "SW9D1eZo",
            "referer": f"https://www.flashscore.ru/match/{mid}/",
            "x-requested-with": "XMLHttpRequest"
        }
        
        # ОДИН запрос, чтобы не вешать Railway
        r = await session.get(url, headers=headers, impersonate="chrome110", timeout=10)
        content = r.text
        
        sh, pn = 0, 0
        # Ищем коды: 158 (Броски), 2 (Штраф)
        parts = content.split('~')
        for p in parts:
            if '158' in p:
                vals = re.findall(r'(\d+)', p)
                if len(vals) >= 2: sh = int(vals[-2]) + int(vals[-1])
            if '2' in p and 'PN' in p:
                vals = re.findall(r'(\d+)', p)
                if len(vals) >= 2: pn = int(vals[-2]) + int(vals[-1])
        
        return sh, pn
    except:
        return 0, 0
