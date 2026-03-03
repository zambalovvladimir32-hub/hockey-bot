import asyncio
import aiohttp
import os
from datetime import datetime, timedelta

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")

# Твой полный список из 35 лиг
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
    """Отправка сообщений в Telegram"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        await session.post(url, json=payload)
    except Exception as e:
        print(f"Ошибка отправки в ТГ: {e}")

async def fetch_json(session, url):
    try:
        async with session.get(url, timeout=10) as r:
            if r.status == 200:
                return await r.json()
    except: pass
    return None

async def main():
    print("--- 🕵️‍♂️ БЭКТЕСТЕР ЗАПУЩЕН ---", flush=True)
    dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, 5)]
    
    total_signals = 0
    goals_1_plus = 0
    goals_2_plus = 0
    
    # Собираем лог матчей, чтобы прикрепить к отчету (если их не миллион)
    matches_log = ""

    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        await send_tg(session, "⏳ <b>БЭКТЕСТЕР ЗАПУЩЕН</b>\nСканирую архивы SofaScore за 4 дня (35 лиг).\n<i>Алгоритм: P1 счет <= 1, удары >= 12, штраф >= 2.</i>\n\nСчитаю результаты 2-го периода... Жди.")

        for date in dates:
            print(f"📅 Качаем архив за {date}...", flush=True)
            url = f"https://api.sofascore.com/api/v1/sport/ice-hockey/scheduled-events/{date}"
            data = await fetch_json(session, url)
            if not data: continue
            
            events = data.get('events', [])
            for ev in events:
                l_name = ev.get('tournament', {}).get('name', '')
                status = ev.get('status', {}).get('code', 0)
                
                if status == 100 and any(t.upper() in l_name.upper() for t in WHITE_LIST):
                    mid = ev.get('id')
                    h_p1 = ev.get('homeScore', {}).get('period1', 0)
                    a_p1 = ev.get('awayScore', {}).get('period1', 0)
                    
                    if (h_p1 + a_p1) <= 1:
                        st_data = await fetch_json(session, f"https://api.sofascore.com/api/v1/event/{mid}/statistics")
                        if not st_data: continue
                        
                        p1 = next((p for p in st_data.get('statistics', []) if p.get('period') == '1ST'), None)
                        if p1:
                            s = {i['key']: int(i.get('homeValue',0)) + int(i.get('awayValue',0)) 
                                 for g in p1.get('groups', []) for i in g.get('statisticsItems', [])}
                            
                            on_g = s.get('shotsOnGoal', 0)
                            pens = s.get('penaltyMinutes', 0)
                            
                            # ПРОГОНЯЕМ ЧЕРЕЗ АЛГОРИТМ
                            if on_g >= 12 and pens >= 2:
                                total_signals += 1
                                h_name = ev.get('homeTeam', {}).get('shortName', 'Home')
                                a_name = ev.get('awayTeam', {}).get('shortName', 'Away')
                                
                                h_p2 = ev.get('homeScore', {}).get('period2', 0)
                                a_p2 = ev.get('awayScore', {}).get('period2', 0)
                                p2_goals = h_p2 + a_p2
                                
                                if p2_goals >= 1: goals_1_plus += 1
                                if p2_goals >= 2: goals_2_plus += 1
                                
                                # Записываем в мини-лог
                                matches_log += f"🔸 {h_name}-{a_name} | Голов во 2-м: <b>{p2_goals}</b>\n"
                        
                        await asyncio.sleep(0.3) # Защита от бана по IP

        # ФОРМИРУЕМ И ОТПРАВЛЯЕМ ИТОГОВЫЙ ОТЧЕТ В ТЕЛЕГУ
        report = f"📊 <b>ИТОГИ БЭКТЕСТА ЗА 4 ДНЯ</b>\n"
        report += f"🔎 Проверено лиг: <b>35</b>\n"
        report += f"🎯 Всего найдено сигналов: <b>{total_signals}</b>\n\n"
        
        if total_signals > 0:
            winrate_1 = (goals_1_plus / total_signals) * 100
            winrate_2 = (goals_2_plus / total_signals) * 100
            report += f"✅ <b>Зашел ТБ 0.5 (1+ гол):</b> {goals_1_plus} из {total_signals} (<b>{winrate_1:.1f}%</b>)\n"
            report += f"🔥 <b>Зашел ТБ 1.5 (2+ гола):</b> {goals_2_plus} из {total_signals} (<b>{winrate_2:.1f}%</b>)\n\n"
            
            # Если матчей не слишком много, прикрепим их список (лимит ТГ - 4096 символов)
            if len(matches_log) < 3000:
                report += f"📝 <b>Список матчей:</b>\n{matches_log}"
            else:
                report += f"📝 <i>Список матчей слишком длинный, чтобы влезть в сообщение.</i>"
        else:
            report += "❌ По твоему алгоритму за 4 дня не нашлось ни одного матча."

        await send_tg(session, report)
        print("✅ Отчет успешно улетел в Телеграм!", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
