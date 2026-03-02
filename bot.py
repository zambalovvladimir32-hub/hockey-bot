async def live_monitor():
    async with AsyncSession() as session:
        print("--- 🚀 v114.0: ПРЯМАЯ ПРОВЕРКА СТАТИСТИКИ LIVESCORE ---")
        while True:
            try:
                # Получаем главный фид
                r = await session.get("https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", 
                                      headers={"x-fsign": "SW9D1eZo"}, impersonate="chrome110")
                blocks = r.text.split('~')
                
                for block in blocks:
                    if 'AA÷' in block:
                        mid = block.split('AA÷')[1].split('¬')[0]
                        
                        # Названия команд
                        h_t = block.split('AE÷')[1].split('¬')[0] if 'AE÷' in block else "Home"
                        a_t = block.split('AF÷')[1].split('¬')[0] if 'AF÷' in block else "Away"
                        
                        # 🔍 ГЛАВНЫЙ ТЕСТ: Берем стату НЕМЕДЛЕННО
                        # Бот принудительно лезет в каждый матч НХЛ/КХЛ
                        sh, pn = await get_flash_stats(session, mid)
                        
                        # ВЫВОД В ЛОГ: Если здесь будут цифры (не 0) - значит тащит!
                        print(f"📊 ПРОВЕРКА СВЯЗИ | {h_t} - {a_t} | Броски: {sh} | Штраф: {pn}")

                print("--- ✅ Цикл проверки завершен, жду 60 сек ---")
            except Exception as e:
                print(f"🛑 КРИТИЧЕСКАЯ ОШИБКА: {e}")
            await asyncio.sleep(60)
