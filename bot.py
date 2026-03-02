import asyncio, re, os, sys
from curl_cffi.requests import AsyncSession

def log(msg):
    print(msg, flush=True)

async def get_fresh_keys(session):
    """Бот сам заходит и забирает актуальный ключ сессии"""
    try:
        r = await session.get("https://www.flashscore.ru/", impersonate="chrome120")
        # Ищем ключ fsign в коде страницы
        key = re.findall(r'fsign["\']\s*:\s*["\']([^"\']+)["\']', r.text)
        return key[0] if key else "SW9D1eZo"
    except:
        return "SW9D1eZo"

async def get_data_stealth(session, mid, fsign):
    """Забираем статистику, прикидываясь живым пользователем"""
    try:
        # Сначала 'кликаем' на матч
        match_url = f"https://www.flashscore.ru/match/{mid}/"
        await session.get(match_url, impersonate="chrome120", timeout=5)
        
        # Теперь тянем саму стату
        url = f"https://www.flashscore.ru/x/feed/df_st_0_{mid}"
        headers = {"x-fsign": fsign, "referer": match_url, "x-requested-with": "XMLHttpRequest"}
        
        r = await session.get(url, headers=headers, impersonate="chrome120", timeout=5)
        
        sh, pn = 0, 0
        if "158" in r.text:
            for s in r.text.split('~'):
                if '158' in s:
                    v = re.findall(r'(\d+)', s)
                    if len(v) >= 2: sh = int(v[-2]) + int(v[-1])
                if '2' in s and 'PN' in s:
                    v = re.findall(r'(\d+)', s)
                    if len(v) >= 2: pn = int(v[-2]) + int(v[-1])
        return sh, pn
    except:
        return 0, 0

async def main():
    log("--- 🧠 v126.0: АВТОНОМНЫЙ РЕЖИМ ---")
    async with AsyncSession() as session:
        while True:
            # 1. Обновляем ключ
            current_fsign = await get_fresh_keys(session)
            log(f"🔑 Ключ захвачен: {current_fsign}")
            
            try:
                # 2. Получаем список матчей
                r = await session.get("https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", 
                                      headers={"x-fsign": current_fsign}, impersonate="chrome120")
                
                mids = re.findall(r'AA÷(.*?)(?=¬)', r.text)[:10]
                for mid in mids:
                    sh, pn = await get_data_stealth(session, mid, current_fsign)
                    if sh > 0:
                        log(f"✅ ВЫТАЩИЛ! Матч {mid} | Броски: {sh} | Штраф: {pn}")
                    else:
                        log(f"🥚 Матч {mid} | Пока пусто")
                
            except Exception as e:
                log(f"🛑 Сбой: {e}")
            await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(main())
