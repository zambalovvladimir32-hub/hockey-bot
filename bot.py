async def live_monitor():
    async with AsyncSession() as session:
        print("--- 🛠 БОТ v113.0: ПРОВЕРКА ПОТОКА ДАННЫХ ---")
        while True:
            try:
                # Читаем Livescore (фид f_4_0_3)
                r = await session.get("https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", 
                                      headers={"x-fsign": "SW9D1eZo"}, impersonate="chrome110")
                blocks = r.text.split('~')
                
                for block in blocks:
                    if 'AA÷' in block:
                        mid = block.split('AA÷')[1].split('¬')[0]
                        
                        # Проверяем, наша ли это лига
                        cur_l = ""
                        if 'ZA÷' in block: cur_l = block.split('ZA÷')[1].split('¬')[0]
                        if not any(l in cur_l for l in WHITE_LIST): continue

                        h_t = block.split('AE÷')[1].split('¬')[0] if 'AE÷' in block else "Home"
                        a_t = block.split('AF÷')[1].split('¬')[0] if 'AF÷' in block else "Away"
                        
                        # ВНИМАНИЕ: Запрашиваем стату ДЛЯ ВСЕХ матчей в списке для теста
                        sh, pn = await get_flash_stats(session, mid)
                        
                        # Выводим в логи Railway ПРЯМО СЕЙЧАС
                        print(f"📈 [DATA-TEST] {h_t} - {a_t} | Броски: {sh} | Штраф: {pn} | Лига: {cur_l}")

                        # А дальше идет старая логика отправки в ТГ только по перерыву
                        # ... (код отправки при AB÷3 и счете <=1)
            
            except Exception as e: print(f"🛑 Error: {e}")
            await asyncio.sleep(60) # Раз в минуту, чтобы не забанили за тест
