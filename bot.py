import asyncio, re, os
from curl_cffi.requests import AsyncSession
from aiogram import Bot

# Настройки из Railway
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

# НАШИ ЛИГИ
WHITE_LIST = [
    'КХЛ', 'ВХЛ', 'МХЛ', 'ЖХЛ', 'НМХЛ', 'НХЛ', 'АХЛ', 
    'АВСТРИЯ: Лига ICE', 'СЛОВАКИЯ: Tipsport liga', 
    'ЧЕХИЯ: Экстралига', 'ЧЕХИЯ: Maxa liga', 'ШВЕЦИЯ: Элитсериен'
]

async def live_monitor():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    processed_matches = set() 

    async with AsyncSession() as session:
        print(f"--- 🚀 БОТ ЗАПУЩЕН (v107.0) ---")
        print(f"📈 Мониторим лиги: {', '.join(WHITE_LIST)}")
        print(f"⚙️ Условия: Перерыв | Счёт <= 1 гола | Броски >= 5 | Штраф >= 2")
        
        while True:
            try:
                # 1. Запрос Flashscore
                r = await session.get("https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", 
                                      headers={"x-fsign": "SW9D1eZo"}, impersonate="chrome110")
                
                blocks = r.text.split('~')
                cur_l = "Unknown"
                
                for block in blocks:
                    if block.startswith('ZA÷'): 
                        cur_l = block.split('ZA÷')[1].split('¬')[0]
                    
                    if block.startswith('AA÷'):
                        mid = block.split('AA÷')[1].split('¬')[0]
                        if mid in processed_matches: continue

                        # Проверка лиги
                        if not any(league in cur_l for league in WHITE_LIST):
                            continue

                        h_team = block.split('AE÷')[1].split('¬')[0] if 'AE÷' in block else "Home"
                        a_team = block.split('AF÷')[1].split('¬')[0] if 'AF÷' in block else "Away"

                        # 1. ТАЙМИНГ: Проверяем перерыв
                        is_break = 'AB÷3' in block or 'NS÷46' in block
                        if not is_break:
                            continue

                        # 2. СЧЁТ: Вытягиваем AG и AH
                        score_data = re.findall(r'AG÷(\d+)¬AH÷(\d+)', block)
                        if score_data:
                            h_g, a_g = map(int, score_data[0])
                            total_g = h_g + a_g
                            
                            if total_g > 1:
                                print(f"❌ [СЧЕТ] {h_team}-{a_team} пропуск ({h_g}:{a_g}) - много голов.")
                                processed_matches.add(mid) # Чтобы больше не проверять этот матч
                                continue

                            # Если счет 0:0, 1:0 или 0:1 — идем на SofaScore
                            print(f"🔍 [АНАЛИЗ] {h_team} - {a_team} ({h_g}:{a_g}). Иду на SofaScore...")
                            
                            q = f"{h_team} {a_team}".split('(')[0].strip()
                            s_req = await session.get(f"https://www.sofascore.com/api/v1/search/all?q={q}", headers=headers)
                            await asyncio.sleep(1.5)
                            
                            res = s_req.json().get('results', [])
                            eid = next((i['entity']['id'] for i in res if i.get('type') == 'event'), None)
                            
                            if eid:
                                st_req = await session.get(f"https://www.sofascore.com/api/v1/event/{eid}/statistics", headers=headers)
                                if st_req.status_code == 200:
                                    data = st_req.json()
                                    sh, pn = 0, 0
                                    for p in data.get('statistics', []):
                                        if p.get('period') in ['1ST', 'ALL']:
                                            for g in p.get('groups', []):
                                                for i in g.get('statisticsItems', []):
                                                    if i['name'] == 'Shots': sh = max(sh, int(i['homeValue']) + int(i['awayValue']))
                                                    if i['name'] == 'Penalty minutes': pn = max(pn, int(i['homeValue']) + int(i['awayValue']))

                                    # 3. СТАТИСТИКА
                                    if sh >= 5 and pn >= 2:
                                        msg = (f"🏟 **ПЕРЕРЫВ (Счёт {h_g}:{a_g})**\n"
                                               f"🏆 {cur_l}\n"
                                               f"🏒 {h_team} — {a_team}\n\n"
                                               f"🎯 Броски в створ: **{sh}**\n"
                                               f"⚖️ Штрафное время: **{pn} мин.**")
                                        await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                        processed_matches.add(mid)
                                        print(f"✅ [СИГНАЛ] Отправлен: {h_team} - {a_team} (Б:{sh}, Ш:{pn})")
                                    else:
                                        print(f"📉 [СТАТА] {h_team}-{a_team}: Броски {sh}, Штраф {pn}. Мало.")
                                        processed_matches.add(mid)
                            else:
                                print(f"⚠️ [SofaScore] Матч {h_team} не найден в поиске.")

            except Exception as e:
                print(f"🛑 [ОШИБКА]: {e}")
            
            await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(live_monitor())
