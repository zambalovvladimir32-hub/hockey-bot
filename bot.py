import asyncio, re, os, sys
from curl_cffi.requests import AsyncSession
from aiogram import Bot

# Функция мгновенного вывода в логи Railway
def log(msg):
    print(msg, flush=True)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

WHITE_LIST = ['КХЛ', 'ВХЛ', 'МХЛ', 'НХЛ', 'АХЛ', 'ICE', 'Tipsport', 'Экстралига', 'Элитсериен']

async def get_stats_with_curl(session, mid):
    """Тянем статистику именно через curl_cffi"""
    try:
        url = f"https://www.flashscore.ru/x/feed/df_st_1_{mid}"
        headers = {
            "x-fsign": "SW9D1eZo",
            "referer": "https://www.flashscore.ru/"
        }
        # Используем имитацию браузера Chrome
        r = await session.get(url, headers=headers, impersonate="chrome110", timeout=15)
        
        sh, pn = 0, 0
        sections = r.text.split('~')
        for s in sections:
            # Парсим броски
            if '158' in s or 'SOG' in s:
                nums = re.findall(r'(\d+)', s)
                if len(nums) >= 2: sh = int(nums[-2]) + int(nums[-1])
            # Парсим штрафы
            if '2' in s and 'PN' in s:
                nums = re.findall(r'(\d+)', s)
                if len(nums) >= 2: pn = int(nums[-2]) + int(nums[-1])
        return sh, pn
    except Exception as e:
        log(f"⚠️ Ошибка в curl_cffi для {mid}: {e}")
        return 0, 0

async def main():
    log("--- 🚀 ЗАПУСК v117.0 (curl_cffi + Force Log) ---")
    
    async with AsyncSession() as session:
        while True:
            try:
                # 1. Загружаем основной фид Livescore
                log("📡 Запрос к главному фиду...")
                r = await session.get("https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", 
                                      headers={"x-fsign": "SW9D1eZo"}, impersonate="chrome110")
                
                blocks = r.text.split('~')
                found_matches = 0
                
                for block in blocks:
                    if 'AA÷' in block:
                        mid = block.split('AA÷')[1].split('¬')[0]
                        
                        # Проверка лиги
                        cur_l = ""
                        if 'ZA÷' in block: cur_l = block.split('ZA÷')[1].split('¬')[0]
                        if not any(l in cur_l for l in WHITE_LIST): continue

                        h_t = block.split('AE÷')[1].split('¬')[0] if 'AE÷' in block else "Home"
                        a_t = block.split('AF÷')[1].split('¬')[0] if 'AF÷' in block else "Away"
                        
                        found_matches += 1
                        
                        # ТЕСТ СТАТИСТИКИ: Тянем её прямо сейчас для логов
                        sh, pn = await get_stats_with_curl(session, mid)
                        log(f"📊 [ST] {h_t} - {a_t} | Броски: {sh} | Штраф: {pn} | Лига: {cur_l}")

                if found_matches == 0:
                    log("📭 Матчей из списка в лайве не найдено.")
                
                log("--- ✅ Проверка завершена, жду 40 сек ---")
            except Exception as e:
                log(f"🛑 ОШИБКА ЦИКЛА: {e}")
            
            await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())
