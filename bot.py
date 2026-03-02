import asyncio, re, os
from curl_cffi.requests import AsyncSession

def log(msg):
    print(msg, flush=True)

async def get_stats_stealth(session, mid):
    try:
        # Пытаемся забрать через "универсальный" технический фид (df_ut)
        # Он часто содержит и инциденты, и статку, и его сложнее заблочить
        url = f"https://www.flashscore.ru/x/feed/df_ut_1_{mid}"
        headers = {
            "x-fsign": "SW9D1eZo",
            "referer": "https://www.flashscore.ru/",
            "x-requested-with": "XMLHttpRequest"
        }
        
        r = await session.get(url, headers=headers, impersonate="chrome120", timeout=10)
        content = r.text
        
        sh, pn = 0, 0
        # Код 158 - броски в створ, 2 - штрафное время
        if "158" in content:
            parts = content.split('~')
            for p in parts:
                if '158' in p:
                    v = re.findall(r'(\d+)', p)
                    if len(v) >= 2: sh = int(v[-2]) + int(v[-1])
                if '2' in p and 'PN' in p:
                    v = re.findall(r'(\d+)', p)
                    if len(v) >= 2: pn = int(v[-2]) + int(v[-1])
            return sh, pn, "OK"
        
        return 0, 0, "NO_STATS_IN_FEED"
    except Exception as e:
        return 0, 0, f"ERR_{e}"

async def main():
    log("--- ⚡️ v130.0: ПЕРЕХВАТЧИК LIVE-ПОТОКА ---")
    async with AsyncSession() as session:
        while True:
            try:
                # Берем список матчей (это работает стабильно)
                r = await session.get("https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", 
                                      headers={"x-fsign": "SW9D1eZo"}, impersonate="chrome120")
                
                mids = re.findall(r'AA÷(.*?)(?=¬)', r.text)[:10]
                log(f"🔎 В эфире {len(mids)} игр. Пробиваю защиту...")

                for mid in mids:
                    sh, pn, status = await get_stats_stealth(session, mid)
                    if sh > 0:
                        log(f"🏒 ЕСТЬ КОНТАКТ! {mid} | Броски: {sh} | Штраф: {pn}")
                    else:
                        log(f"🥚 {mid} | {status}")

            except Exception as e:
                log(f"🛑 Ошибка: {e}")
            await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())
