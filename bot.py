async def get_fresh_fsign(session):
    """Пытаемся вытянуть актуальный ключ прямо из кода страницы"""
    try:
        r = await session.get("https://www.flashscore.ru/", impersonate="chrome120")
        # Ищем ключ в скриптах (обычно это 8 символов типа SW9D1eZo)
        found = re.findall(r'fsign["\']\s*:\s*["\']([^"\']+)["\']', r.text)
        if found:
            return found[0]
        return "SW9D1eZo" # Запасной вариант
    except:
        return "SW9D1eZo"

async def main():
    log("--- ⚡️ v125.0: АВТО-ЗАХВАТ КЛЮЧЕЙ ---")
    async with AsyncSession() as session:
        while True:
            # 1. ОБНОВЛЯЕМ КЛЮЧ ПЕРЕД КАЖДЫМ ЦИКЛОМ
            fsign = await get_fresh_fsign(session)
            log(f"🔑 Актуальный ключ: {fsign}")
            
            try:
                # 2. Запрашиваем лайв с НОВЫМ ключом
                r = await session.get("https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", 
                                      headers={"x-fsign": fsign}, impersonate="chrome120")
                
                matches = re.findall(r'AA÷(.*?)(?=¬)', r.text)
                for mid in matches[:5]:
                    # 3. Пробуем забрать статистику
                    url = f"https://www.flashscore.ru/x/feed/df_st_0_{mid}"
                    res = await session.get(url, headers={"x-fsign": fsign}, impersonate="chrome120")
                    
                    if "158" in res.text:
                        # УРА! МЫ ПРОБИЛИСЬ!
                        sh, pn = 0, 0
                        # ... тут парсинг ...
                        log(f"✅ УДАЧА! Матч {mid} | Броски: {sh}")
                    else:
                        log(f"❌ Матч {mid} | Данные заблокированы сервером")

            except Exception as e: log(f"🛑 Ошибка: {e}")
            await asyncio.sleep(45)
