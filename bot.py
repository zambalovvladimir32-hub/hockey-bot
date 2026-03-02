async def get_stats_with_curl(session, mid, is_break):
    try:
        # 1. Сначала пробуем специфический фид для 1-го ПЕРИОДА
        url_period = f"https://www.flashscore.ru/x/feed/df_st_1_{mid}"
        # 2. Параллельно имеем в виду фид ОБЩЕЙ статы (на всякий случай)
        url_all = f"https://www.flashscore.ru/x/feed/df_st_0_{mid}"
        
        target_url = url_period if is_break else url_all
        
        headers = {
            "x-fsign": "SW9D1eZo",
            "referer": f"https://www.flashscore.ru/match/{mid}/",
            "x-requested-with": "XMLHttpRequest"
        }
        
        r = await session.get(target_url, headers=headers, impersonate="chrome110", timeout=10)
        
        # Если фид периода пустой, пробуем общий фид
        if '158' not in r.text and is_break:
             r = await session.get(url_all, headers=headers, impersonate="chrome110", timeout=10)

        content = r.text
        sh, pn = 0, 0
        for s in content.split('~'):
            if '158' in s:
                v = re.findall(r'(\d+)', s)
                if len(v) >= 2: sh = int(v[-2]) + int(v[-1])
            if '2' in s and 'PN' in s:
                v = re.findall(r'(\d+)', s)
                if len(v) >= 2: pn = int(v[-2]) + int(v[-1])
        
        return sh, pn
    except:
        return 0, 0
