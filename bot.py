import asyncio
import aiohttp
import os
from datetime import datetime, timedelta

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")

WHITE_LIST = [
    "1st Liga", "1st Liga Playoffs", "AHL", "Alps Hockey League, Championship Round",
    "Alps Hockey League, Qualification Round, Group B", "Asia League",
    "Auroraliiga, Women, Playoffs", "DEL", "Ekstraliga, Playoffs", "EliteHockey Ligaen",
    "Extraliga", "Hockey Allsvenskan", "HockeyEttan Sodra", "ICE Hockey League",
    "KHL", "Ligue Magnus", "Liiga", "MHL", "Mestis", "Mestis Playoffs", "NHL",
    "National League", "OHL", "PWHL", "SDHL", "SHL", "Swiss League, Playoffs",
    "Tipsport Liga", "U20 Elite, Qualifying Round", "U20 Extraliga Juniorov",
    "U20 Extraliga Junioru, Championship Round", "U20 Extraliga Junioru, Qualification Round",
    "University League", "VHL", "WHL, Women"
]

async def send_tg(session, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        await session.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
    except: pass

async def main():
    print("--- 🕵️‍♂️ БЭКТЕСТЕР V3 (ПОЛИГЛОТ) ЗАПУЩЕН ---", flush=True)
    dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, 5)]
    
    total_signals = 0
    goals_1_plus = 0
    goals_2_plus = 0
    matches_log = ""

    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        await send_tg(session, "⏳ <b>БЭКТЕСТЕР V3 ЗАПУЩЕН</b>\nДобавлена поддержка русского языка ('Выстрелы', '1-й'). Ищу матчи... Жди.")

        for date in dates:
            print(f"📅 Качаем архив за {date}...", flush=True)
            try:
                async with session.get(f"https://api.sofascore.com/api/v1/sport/ice-hockey/scheduled-events/{date}", timeout=10) as r:
                    if r.status != 200: continue
                    events = (await r.json()).get('events', [])
            except: continue
            
            for ev in events:
                l_name = ev.get('tournament', {}).get('name', '')
                if ev.get('status', {}).get('code', 0) == 100 and any(t.upper() in l_name.upper() for t in WHITE_LIST):
                    mid = ev.get('id')
                    h_p1 = ev.get('homeScore', {}).get('period1', 0)
                    a_p1 = ev.get('awayScore', {}).get('period1', 0)
                    
                    if (h_p1 + a_p1) <= 1:
                        try:
                            async with session.get(f"https://api.sofascore.com/api/v1/event/{mid}/statistics", timeout=10) as rs:
                                if rs.status != 200: continue
                                st_data = await rs.json()
                        except: continue
                        
                        # ИЩЕМ ПЕРИОД (1ST, 1st, 1-й)
                        p1 = None
                        for p in st_data.get('statistics', []):
                            p_name = str(p.get('period', '')).lower()
                            if '1st' in p_name or '1-й' in p_name or p_name == '1':
                                p1 = p
                                break
                        
                        if p1:
                            on_g, pens = 0, 0
                            
                            # ИЩЕМ БРОСКИ И ШТРАФЫ НА ВСЕХ ЯЗЫКАХ
                            for g in p1.get('groups', []):
                                for i in g.get('statisticsItems', []):
                                    key_raw = str(i.get('key', '')).lower().replace(' ', '')
                                    name_raw = str(i.get('name', '')).lower().replace(' ', '')
                                    val = int(i.get('homeValue', 0)) + int(i.get('awayValue', 0))
                                    
                                    # Проверяем "shots", "выстрелы", "удары в створ"
                                    if any(x in key_raw or x in name_raw for x in ['shots', 'выстрелы', 'удары']):
                                        on_g = val
                                        
                                    # Проверяем "penalties", "штраф", "удаления"
                                    if any(x in key_raw or x in name_raw for x in ['penalty', 'penalties', 'штраф', 'удалени']):
                                        pens = val
                            
                            if on_g >= 12 and pens >= 2:
                                total_signals += 1
                                h_name = ev.get('homeTeam', {}).get('shortName', 'Home')
                                a_name = ev.get('awayTeam', {}).get('shortName', 'Away')
                                
                                h_p2 = ev.get('homeScore', {}).get('period2', 0)
                                a_p2 = ev.get('awayScore', {}).get('period2', 0)
                                p2_goals = h_p2 + a_p2
                                
                                if p2_goals >= 1: goals_1_plus += 1
                                if p2_goals >= 2: goals_2_plus += 1
                                
                                matches_log += f"🔸 {h_name}-{a_name} ({on_g} уд.) | Голов во 2-м: <b>{p2_goals}</b>\n"
                        
                        await asyncio.sleep(0.3)

        report = f"📊 <b>ИТОГИ БЭКТЕСТА ЗА 4 ДНЯ (V3)</b>\n"
        report += f"🔎 Проверено лиг: <b>35</b>\n"
        report += f"🎯 Найдено сигналов: <b>{total_signals}</b>\n\n"
        
        if total_signals > 0:
            winrate_1 = (goals_1_plus / total_signals) * 100
            winrate_2 = (goals_2_plus / total_signals) * 100
            report += f"✅ <b>Зашел ТБ 0.5 (1+ гол во 2-м):</b> {goals_1_plus} из {total_signals} (<b>{winrate_1:.1f}%</b>)\n"
            report += f"🔥 <b>Зашел ТБ 1.5 (2+ гола во 2-м):</b> {goals_2_plus} из {total_signals} (<b>{winrate_2:.1f}%</b>)\n\n"
            
            if len(matches_log) < 3000:
                report += f"📝 <b>Список матчей:</b>\n{matches_log}"
            else:
                report += f"📝 <i>Список матчей слишком длинный.</i>"
        else:
            report += "❌ 0 сигналов. Если и сейчас ноль, значит я съем свою виртуальную шляпу."

        await send_tg(session, report)
        print("✅ Отчет отправлен!", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
