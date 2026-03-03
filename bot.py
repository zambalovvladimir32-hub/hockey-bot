import asyncio
import aiohttp
import os
import json
import google.generativeai as genai

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

WHITE_LIST = ["KHL", "NHL", "SHL", "Liiga", "DEL", "Extraliga", "VHL"]
SENT_SIGNALS = set()

async def ai_partner_decision(home, away, score, s_map):
    """ИИ анализирует, стоит ли заходить, если стата 'плавает' около 13"""
    on_goal = s_map.get('on_goal', 0)
    total = on_goal + s_map.get('blocked', 0) + s_map.get('wide', 0)
    
    prompt = f"""
    Матч {home}-{away}, Счет P1 {score}. 
    Броски в створ: {on_goal}. Всего попыток (вкл. блоки и мимо): {total}.
    Штрафы: {s_map.get('penalties', 0)} мин.
    
    ЗАДАЧА:
    Если бросков в створ 11-12, но общая активность высокая (>17 попыток) и есть штрафы — это СИГНАЛ.
    Ответь строго: ВЕРДИКТ [ЗАХОДИМ/НЕТ] и почему.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except: return "ВЕРДИКТ [ЗАХОДИМ]"

async def main():
    print("--- 🚀 v173.0: ФИНАЛЬНАЯ СИНЕРГИЯ ЗАПУЩЕНА ---", flush=True)

    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        while True:
            try:
                async with session.get("https://api.sofascore.com/api/v1/sport/ice-hockey/events/live") as r:
                    if r.status != 200: continue
                    events = (await r.json()).get('events', [])

                for ev in events:
                    mid = ev.get('id')
                    if mid in SENT_SIGNALS or ev.get('status', {}).get('code') != 31: continue
                    
                    if not any(t.upper() in ev.get('tournament', {}).get('name', '').upper() for t in WHITE_LIST): continue

                    h_p1, a_p1 = ev.get('homeScore', {}).get('period1', 0), ev.get('awayScore', {}).get('period1', 0)
                    if (h_p1 + a_p1) > 1: continue

                    async with session.get(f"https://api.sofascore.com/api/v1/event/{mid}/statistics") as rs:
                        if rs.status != 200: continue
                        st_data = await rs.json()
                        p1 = next((p for p in st_data.get('statistics', []) if p.get('period') == '1ST'), None)
                        if not p1: continue

                        s_map = {}
                        for g in p1.get('groups', []):
                            for i in g.get('statisticsItems', []):
                                key, h, a = i['key'], int(i.get('homeValue',0)), int(i.get('awayValue',0))
                                if key == 'shotsOnGoal': s_map['on_goal'] = h + a
                                if key == 'blockedShots': s_map['blocked'] = h + a
                                if key == 'shotsWide': s_map['wide'] = h + a
                                if key in ['penaltyMinutes', 'penalties']: s_map['penalties'] = h + a

                        on_g = s_map.get('on_goal', 0)
                        pens = s_map.get('penalties', 0)
                        total_att = on_g + s_map.get('blocked', 0) + s_map.get('wide', 0)

                        # ГИБКИЙ ПОРОГ ПОД ТВОИ СКРИНЫ:
                        # Если 13+ — летим сразу. 
                        # Если 11-12 (как у Амура), но общее давление есть — зовем ИИ.
                        if (on_g >= 13 or (on_g >= 11 and total_att >= 18)) and pens >= 2:
                            home, away = ev['homeTeam']['shortName'], ev['awayTeam']['shortName']
                            verdict = await ai_partner_decision(home, away, f"{h_p1}:{a_p1}", s_map)
                            
                            if "ЗАХОДИМ" in verdict.upper():
                                msg = (
                                    f"🔥 <b>СИГНАЛ: {home} — {away}</b>\n"
                                    f"🥅 Счет P1: <b>{h_p1}:{a_p1}</b>\n"
                                    f"🎯 В створ: <b>{on_g}</b> | ⏳ Штраф: <b>{pens}м</b>\n"
                                    f"🏒 Всего попыток: <b>{total_att}</b>\n"
                                    f"━━━━━━━━━━━━━━━━━━\n"
                                    f"🧠 <b>AI:</b> {verdict.strip()}"
                                )
                                await session.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                                 json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})
                                SENT_SIGNALS.add(mid)

            except Exception as e: print(f"Error: {e}")
            await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(main())
