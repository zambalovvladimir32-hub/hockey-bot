import asyncio, re, os, sys
import aiohttp

def log(msg):
    print(msg, flush=True)

# Этот ключ нужно будет менять раз в пару дней, если полетят нули
# Сейчас попробуем пробить через мобильный API
FSIGN = "SW9D1eZo" 

async def get_stats(session, mid):
    try:
        # Тянем через мобильную версию, она менее защищена
        url = f"https://m.flashscore.ru/x/feed/df_st_0_{mid}"
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
            "x-fsign": FSIGN,
            "x-requested-with": "XMLHttpRequest",
            "Referer": f"https://m.flashscore.ru/match/{mid}/"
        }
        async with session.get(url, headers=headers, timeout=10) as r:
            text = await r.text()
            if "158" not in text: return 0, 0
            
            sh, pn = 0, 0
            for part in text.split('~'):
                if '158' in part:
                    nums = re.findall(r'(\d+)', part)
                    if len(nums) >= 2: sh = int(nums[-2]) + int(nums[-1])
                if '2' in part and 'PN' in part:
                    nums = re.findall(r'(\d+)', part)
                    if len(nums) >= 2: pn = int(nums[-2]) + int(nums[-1])
            return sh, pn
    except: return 0, 0

async def main():
    log("--- ⚡️ v128.0: ОПТИМИЗИРОВАННЫЙ АНТИ-ЛОМ ---")
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                # Берем список матчей
                async with session.get(f"https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", headers={"x-fsign": FSIGN}) as r:
                    data = await r.text()
                
                mids = re.findall(r'AA÷(.*?)(?=¬)', data)[:10]
                log(f"🔎 Вижу {len(mids)} матчей. Погнали...")

                for mid in mids:
                    sh, pn = await get_stats(session, mid)
                    if sh > 0 or pn > 0:
                        log(f"🏒 МАТЧ {mid} | БРОСКИ: {sh} | ШТРАФ: {pn} ✅")
                    else:
                        log(f"🥚 МАТЧ {mid} | Пусто")

            except Exception as e: log(f"🛑 Сбой: {e}")
            await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())
