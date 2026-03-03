import asyncio
import aiohttp
import os
import json
import google.generativeai as genai

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

WHITE_LIST = ["KHL", "NHL", "SHL", "Liiga", "DEL", "Extraliga"]
SENT_SIGNALS = set()

async def ai_verify(home, away, score, s_map, raw_data):
    """ИИ копается в деталях, чтобы понять, не занижена ли стата"""
    prompt = f"""
    Матч {home}-{away}, Счет P1 {score}. 
    SofaScore дает: В створ {s_map.get('on_goal', 0)}, Блокировано {s_map.get('blocked', 0)}, Мимо {s_map.get('wide', 0)}.
    Штрафы: {s_map.get('penalties', 0)} мин.
    
    ВОПРОС: Стоит ли заходить на ТБ во 2-м периоде? 
    Если бросков в створ 10-12, но много блокированных (5+) — это наш клиент.
    Если штрафов 2 мин, но игра была грубой (много инцидентов) — это наш клиент.
    
    Ответь коротко: ВЕРДИКТ [ДА/НЕТ] и ПРИЧИНА.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except: return "ВЕРДИКТ [ДА]"

async def main():
    print("--- 🚀 v171.0: ИСПРАВЛЕННЫЙ АНАЛИЗ ЗАПУЩЕН ---", flush=True)

    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        while True:
            try:
                async with session.get("https://api.sofascore.com/api/v1/sport/ice-hockey/events/live") as r:
                    if r.status != 200: continue
                    events = (await r.json()).get('events', [])

                for ev in events:
                    mid = ev.get('id')
                    if mid in SENT_SIGNALS or ev.get('status', {}).get('code') != 31: continue
                    
                    # Фильтр лиги
                    if not any(t.upper() in ev.get('tournament', {}).get('name', '').upper() for t in WHITE_LIST): continue

                    h_p1, a_p1 = ev.get('homeScore', {}).get('period1', 0), ev.get('awayScore', {}).get('period1', 0)
                    if (h_p1 + a_p1) > 1: continue

                    # Забираем глубокую стату
                    async with session.get(f"https://api.sofascore.com/api/v1/event/{mid}/statistics") as rs:
                        if rs.status != 200: continue
                        st_data = await rs.json()
                        p1 = next((p for p in st_data.get('statistics', []) if p.get('period') == '1ST'), None)
                        if not p1: continue

                        # Собираем свою карту бросков
                        s_map = {}
                        for g in p1.get('groups', []):
                            for i in g.get('statisticsItems', []):
                                if i['key'] == 'shotsOnGoal': s_map['on_goal'] = int(i.get('homeValue',0)) + int(i.get('awayValue',0))
                                if i['key'] == 'blockedShots': s_map['blocked'] = int(i.get('homeValue',0)) + int(i.get('awayValue',0))
                                if i['key'] == 'shotsWide': s_map['wide'] = int(i.get('homeValue',0)) + int(i.get('awayValue',0))
                                if i['key'] in ['penaltyMinutes', 'penalties']: s_map['penalties'] = int(i.get('homeValue',0)) + int(i.get('awayValue',0))

                        shots = s_map.get('on_goal', 0)
                        pens = s_map.get('penalties', 0)
                        total_att = shots + s_map.get('blocked', 0) + s_map.get('wide', 0)

                        # ГИБКИЙ ПОРОГ: Если 13+ — сигнал сразу. Если 10-12, но попыток дофига — зовем ИИ.
                        if (shots >= 13 or (shots >= 10 and total_att >= 18)) and pens >= 2:
                            home, away = ev['homeTeam']['shortName'], ev['awayTeam']['shortName']
                            verdict = await ai_verify(home, away, f"{h_p1}:{a_p1}", s_map, st_data)
                            
                            if "ДА" in verdict.upper():
                                msg = (
                                    f"🏒 <b>СИГНАЛ: {home} — {away}</b>\n"
                                    f"🥅 Счет P1: <b>{h_p1}:{a_p1}</b>\n"
                                    f"🎯 В створ: <b>{shots}</b> | ⏳ Штраф: <b>{pens}м</b>\n"
                                    f"🔥 Всего попыток: <b>{total_att}</b>\n"
                                    f"━━━━━━━━━━━━━━━━━━\n"
                                    f"🤖 <b>AI-АНАЛИЗ:</b> {verdict.strip()}"
                                )
                                await session.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                                 json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})
                                SENT_SIGNALS.add(mid)

            except Exception as e: print(f"Error: {e}")
            await asyncio.sleep(25)

if __name__ == "__main__":
    asyncio.run(main())
