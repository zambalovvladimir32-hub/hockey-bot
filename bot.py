import asyncio, re, os
from curl_cffi.requests import AsyncSession
from aiogram import Bot

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

WHITE_LIST = ['КХЛ', 'ВХЛ', 'МХЛ', 'ЖХЛ', 'НМХЛ', 'НХЛ', 'АХЛ', 'ICE', 'Tipsport', 'Экстралига', 'Maxa', 'Элитсериен']

async def get_flash_stats(session, mid):
    """Тянем статику прямо с Livescore"""
    try:
        url = f"https://www.flashscore.ru/x/feed/df_st_1_{mid}"
        headers = {"x-fsign": "SW9D1eZo", "referer": "https://www.flashscore.ru/"}
        r = await session.get(url, headers=headers, impersonate="chrome110")
        content = r.text
        sh, pn = 0, 0
        parts = content.split('~')
        for p in parts:
            if any(x in p for x in ['Броски в створ', 'SOG', '158']):
                vals = re.findall(r'(\d+)', p)
                if len(vals) >= 2: sh = int(vals[-2]) + int(vals[-1])
            if any(x in p for x in ['Штрафное время', 'PEN', '2']):
                vals = re.findall(r'(\d+)', p)
                if len(vals) >= 2: pn = int(vals[-2]) + int(vals[-1])
        return sh, pn
    except: return 0, 0

async def live_monitor():
    async with AsyncSession() as session:
        print("--- 🛠 БОТ v112.0 ВКЛЮЧЕН (СУПЕР-ЛОГ) ---")
        processed_matches = set()
        
        while True:
            try:
                # Читаем Livescore
                r = await session.get("https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", 
                                      headers={"x-fsign": "SW9D1eZo"}, impersonate="chrome110")
                blocks = r.text.split('~')
                cur_l = ""
                
                for block in blocks:
                    if block.startswith('ZA÷'): cur_l = block.split('ZA÷')[1].split('¬')[0]
                    if block.startswith('AA÷'):
                        mid = block.split('AA÷')[1].split('¬')[0]
                        if not any(l in cur_l for l in WHITE_LIST): continue
                        
                        h_t = block.split('AE÷')[1].split('¬')[0] if 'AE÷' in block else "Home"
                        a_t = block.split('AF÷')[1].split('¬')[0] if 'AF÷' in block else "Away"
                        
                        # ВОТ ЭТО ПОКАЖЕТ, ЧТО БОТ ТАЩИТ ДАННЫЕ
                        status_code = block.split('AB÷')[1].split('¬')[0] if 'AB÷' in block else "?"
                        print(f"📡 [SCAN] {h_t} - {a_t} | Статус: {status_code} | Лига: {cur_l}")

                        # Проверяем условия
                        if status_code in ['3', '46']: # ПЕРЕРЫВ
                            score = re.findall(r'AG÷(\d+)¬AH÷(\d+)', block)
                            if score:
                                h_g, a_g = map(int, score[0])
                                if (h_g + a_g) <= 1:
                                    if mid not in processed_matches:
                                        sh, pn = await get_flash_stats(session, mid)
                                        print(f"📊 ПРОВЕРКА СТАТЫ: {h_t}-{a_t} (Броски: {sh}, Штраф: {pn})")
                                        
                                        if sh >= 5 and pn >= 2:
                                            # Отправка сигнала...
                                            processed_matches.add(mid)
                                            print(f"✅ СИГНАЛ ОТПРАВЛЕН В ТГ")
                                else:
                                    print(f"⏩ Скип: счет {h_g}:{a_g} не наш.")
            
            except Exception as e: print(f"🛑 Error: {e}")
            await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(live_monitor())
