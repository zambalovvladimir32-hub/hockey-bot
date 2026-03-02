async def get_data_stealth(session, mid, fsign):
    try:
        # ШАГ 1: Имитируем полный заход на страницу матча для получения Cookie
        match_url = f"https://www.flashscore.ru/match/{mid}/"
        # Сохраняем куки после этого запроса
        response_main = await session.get(match_url, impersonate="chrome120", timeout=10)
        
        # ШАГ 2: Запрашиваем статистику, используя полученные куки и правильный реферер
        url = f"https://www.flashscore.ru/x/feed/df_st_0_{mid}"
        headers = {
            "x-fsign": fsign,
            "referer": match_url,
            "x-requested-with": "XMLHttpRequest",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        
        r = await session.get(url, headers=headers, impersonate="chrome120", timeout=10)
        
        # Если в логе видим 'AS÷', значит мы пробили защиту
        if "AS÷" in r.text:
            sh, pn = 0, 0
            for s in r.text.split('~'):
                if '158' in s: # Броски
                    v = re.findall(r'(\d+)', s)
                    if len(v) >= 2: sh = int(v[-2]) + int(v[-1])
                if '2' in s and 'PN' in s: # Штраф
                    v = re.findall(r'(\d+)', s)
                    if len(v) >= 2: pn = int(v[-2]) + int(v[-1])
            return sh, pn
        return 0, 0
    except:
        return 0, 0
