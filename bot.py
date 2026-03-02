async def get_everything(session, mid):
    """Пытаемся вытащить ВООБЩЕ ВСЕ данные по матчу"""
    try:
        # Пробуем 3 разных фида: общая стата, стата 1-го периода и инциденты
        feeds = [f"df_st_0_{mid}", f"df_st_1_{mid}", f"df_ut_{mid}"]
        combined_text = ""
        
        for feed in feeds:
            url = f"https://www.flashscore.ru/x/feed/{feed}"
            headers = {
                "x-fsign": "SW9D1eZo", # Если этот ключ сдох, мы увидим ошибку 403
                "referer": f"https://www.flashscore.ru/match/{mid}/",
                "x-requested-with": "XMLHttpRequest"
            }
            r = await session.get(url, headers=headers, impersonate="chrome120", timeout=7)
            combined_text += r.text + " "

        # Если в ответе есть хоть одна цифра в формате статистики (AS÷)
        # Мы выводим кусок текста в лог, чтобы понять, ЧТО там вообще лежит
        if "AS÷" in combined_text:
            # Ищем броски (158) и штраф (2)
            sh = 0
            pn = 0
            for part in combined_text.split('~'):
                if '158' in part:
                    v = re.findall(r'(\d+)', part)
                    if len(v) >= 2: sh = int(vals[-2]) + int(vals[-1])
                if '2' in part and 'PN' in part:
                    v = re.findall(r'(\d+)', part)
                    if len(v) >= 2: pn = int(vals[-2]) + int(vals[-1])
            return sh, pn, "OK"
        else:
            return 0, 0, "EMPTY_OR_LOCKED"
    except Exception as e:
        return 0, 0, f"ERROR_{e}"

async def main():
    log("--- 🚨 v124.0: ГЛУБОКОЕ СКАНИРОВАНИЕ ---")
    async with AsyncSession() as session:
        while True:
            try:
                # Читаем лайв
                r = await session.get("https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", 
                                      headers={"x-fsign": "SW9D1eZo"}, impersonate="chrome120")
                
                # Ищем матчи из твоего списка (НХЛ, КХЛ и т.д.)
                matches = re.findall(r'AA÷(.*?)(?=¬)', r.text)
                
                for mid in matches[:10]:
                    sh, pn, status = await get_everything(session, mid)
                    # Выводим подробный отчет по каждому запросу
                    log(f"🔎 Матч {mid} | Статус: {status} | Броски: {sh} | Штраф: {pn}")

                log("--- Цикл завершен ---")
            except Exception as e: log(f"🛑 Ошибка: {e}")
            await asyncio.sleep(45)
