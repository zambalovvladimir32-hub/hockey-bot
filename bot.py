import asyncio, re, os
from curl_cffi.requests import AsyncSession
from aiogram import Bot

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

WHITE_LIST = [
    'АВСТРИЯ: Лига ICE', 'РОССИЯ: OLIMPBET - МХЛ', 'РОССИЯ: ЖХЛ', 
    'СЛОВАКИЯ: Tipsport liga', 'ЧЕХИЯ: Maxa liga', 'ЧЕХИЯ: Экстралига', 
    'ШВЕЦИЯ: Элитсериен', 'КХЛ', 'ВХЛ', 'НМХЛ', 'НХЛ', 'АХЛ'
]

async def get_flash_stats(session, mid):
    """Глубокий парсинг статистики Flashscore/Livescore"""
    try:
        # 1. Сначала 'прогреваем' сессию, заходя на матч
        await session.get(f"https://www.flashscore.ru/match/{mid}/", impersonate="chrome110")
        
        # 2. Теперь дергаем саму статистику
        url = f"https://www.flashscore.ru/x/feed/df_st_1_{mid}"
        headers = {
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "XMLHttpRequest",
            "referer": f"https://www.flashscore.ru/match/{mid}/"
        }
        r = await session.get(url, headers=headers, impersonate="chrome110")
        
        content = r.text
        sh, pn = 0, 0
        
        # Разделяем по категориям статистики
        parts = content.split('~')
        for p in parts:
            # Ищем Броски (SOG)
            if any(x in p for x in ['Броски в створ', 'SOG', '158']):
                vals = re.findall(r'(\d+)', p)
                if len(vals) >= 2: sh = int(vals[-2]) + int(vals[-1])
            # Ищем Штраф (PEN)
            if any(x in p for x in ['Штрафное время', 'PEN', '2']):
                vals = re.findall(r'(\d+)', p)
                if len(vals) >= 2: pn = int(vals[-2]) + int(vals[-1])
        
        return sh, pn
    except Exception as e:
        print(f"⚠️ Ошибка парсинга статы {mid}: {e}")
        return 0, 0

async def live_monitor():
    async with AsyncSession() as session:
        print("🚀 v110.0: Прямой мониторинг Livescore с эмуляцией сессии...")
        processed_matches = set()
        
        while True:
            try:
                # Обновляем основной фид
                r = await session.get("https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", 
                                      headers={"x-fsign": "SW9D1eZo"}, impersonate="chrome110")
                blocks = r.text.split('~')
                cur_l = ""
                
                for block in blocks:
                    if block.startswith('ZA÷'): 
                        cur_l = block.split('ZA÷')[1].split('¬')[0]
                    
                    if block.startswith('AA÷'):
                        mid = block.split('AA÷')[1].split('¬')[0]
                        if mid in processed_matches: continue
                        
                        if not any(l in cur_l for l in WHITE_LIST): continue

                        # ПЕРЕРЫВ (3 или 46) + Счёт <= 1 гола
                        is_break = 'AB÷3' in block or 'NS÷46' in block
                        score = re.findall(r'AG÷(\d+)¬AH÷(\d+)', block)
                        
                        if is_break and score:
                            h_g, a_g = map(int, score[0])
                            if (h_g + a_g) <= 1:
                                h_team = block.split('AE÷')[1].split('¬')[0]
                                a_team = block.split('AF÷')[1].split('¬')[0]
                                
                                # Берем стату напрямую
                                sh, pn = await get_flash_stats(session, mid)
                                print(f"📊 {h_team}-{a_team}: Броски {sh}, Штраф {pn}")
                                
                                if sh >= 5 and pn >= 2:
                                    msg = (f"🏟 **ПЕРЕРЫВ (Счёт {h_g}:{a_g})**\n"
                                           f"🏆 {cur_l}\n🏒 {h_team} — {a_team}\n\n"
                                           f"🎯 Броски (Livescore): **{sh}**\n"
                                           f"⚖️ Штраф: **{pn} мин.**")
                                    await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                    processed_matches.add(mid)
                                    print(f"✅ СИГНАЛ ОТПРАВЛЕН")

            except Exception as e:
                print(f"🛑 Ошибка цикла: {e}")
            await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(live_monitor())
