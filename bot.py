import asyncio, re, os, sys
from curl_cffi.requests import AsyncSession

def log(msg):
    print(msg, flush=True)

# ТВОЙ РАБОЧИЙ КЛЮЧ
WORKING_FSIGN = "SW9D1eZo"

async def get_stats_hard(session, mid):
    try:
        # 1. Сначала ОБЯЗАТЕЛЬНО заходим на страницу матча (имитируем клик человека)
        match_url = f"https://www.flashscore.ru/match/{mid}/#/match-summary/match-statistics/0"
        await session.get(match_url, impersonate="chrome120", timeout=10)
        
        # 2. Теперь стучимся в фид статистики с тем самым ключом
        # df_st_0 - общая стата, df_st_1 - первый период
        stats_url = f"https://www.flashscore.ru/x/feed/df_st_0_{mid}"
        
        headers = {
            "x-fsign": WORKING_FSIGN,
            "referer": match_url,
            "x-requested-with": "XMLHttpRequest"
        }
        
        r = await session.get(stats_url, headers=headers, impersonate="chrome120", timeout=10)
        raw_data = r.text
        
        # ПРОВЕРКА: Если в ответе есть код 158 (броски) или 2 (штраф)
        sh, pn = 0, 0
        if "158" in raw_data or "AS÷" in raw_data:
            for s in raw_data.split('~'):
                if '158' in s:
                    nums = re.findall(r'(\d+)', s)
                    if len(nums) >= 2: sh = int(nums[-2]) + int(nums[-1])
                if '2' in s and 'PN' in s:
                    nums = re.findall(r'(\d+)', s)
                    if len(nums) >= 2: pn = int(nums[-2]) + int(nums[-1])
            return sh, pn, "OK"
        
        return 0, 0, "EMPTY_RESPONSE"
    except Exception as e:
        return 0, 0, f"ERROR: {e}"

async def main():
    log(f"--- 🏒 v129.0: ТЕСТ С КЛЮЧОМ {WORKING_FSIGN} ---")
    async with AsyncSession() as session:
        # Заходим на главную один раз для общих куки
        await session.get("https://www.flashscore.ru/", impersonate="chrome120")
        
        while True:
            try:
                # Получаем список матчей
                r = await session.get(f"https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", 
                                      headers={"x-fsign": WORKING_FSIGN}, impersonate="chrome120")
                
                mids = re.findall(r'AA÷(.*?)(?=¬)', r.text)[:8] # Берем 8 матчей
                log(f"🔎 Вижу {len(mids)} матчей в лайве. Вытаскиваю стату...")

                for mid in mids:
                    sh, pn, status = await get_stats_hard(session, mid)
                    if status == "OK" and (sh > 0 or pn > 0):
                        log(f"✅ ВЫТАЩИЛ! Матч {mid} | Броски: {sh} | Штраф: {pn}")
                    else:
                        log(f"🥚 Матч {mid} | Статус: {status} | Броски: {sh}")

            except Exception as e:
                log(f"🛑 Ошибка цикла: {e}")
            
            await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(main())
