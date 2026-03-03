import asyncio
import aiohttp
import os
from google import genai

# Инициализация нового клиента API (без варнингов)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")

WHITE_LIST = ["KHL", "NHL", "SHL", "Liiga", "DEL", "Extraliga", "VHL"]
SENT_SIGNALS = set()

async def ai_decision(home, away, score, s_map):
    """ИИ как финальный судья: подтверждает вход при 'плавающей' стате"""
    on_g = s_map.get('on_goal', 0)
    total = on_g + s_map.get('blocked', 0) + s_map.get('wide', 0)
    
    prompt = f"Матч {home}-{away}, P1 {score}. В створ {on_g}, блоки {s_map.get('blocked', 0)}, мимо {s_map.get('wide', 0)}. Штраф {s_map.get('penalties', 0)} мин. Если общее давление >17 — пиши 'ЗАХОДИМ', иначе 'НЕТ'."
    
    try:
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        return response.text
    except: return "ЗАХОДИМ"

async def main():
    print("--- ⚔️ v174.0: СИСТЕМА ПЕРЕЗАПУЩЕНА (НОВЫЙ КЛИЕНТ) ---", flush=True)

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
                                key, h, a = i['key'], int(i.get('homeValue', 0)), int(i.get('awayValue', 0))
                                if key == 'shotsOnGoal': s_map['on_goal'] = h + a
                                if key == 'blockedShots': s_map['blocked'] = h + a
                                if key == 'shotsWide': s_map['wide'] = h + a
                                if key in ['penaltyMinutes', 'penalties']: s_map['penalties'] = h + a

                        on_g = s_map.get('on_goal', 0)
                        pens = s_map.get('penalties', 0)
                        total_att = on_g + s_map.get('blocked', 0) + s_map.get('wide', 0)

                        # ЛОГИКА ПОД ТВОИ СКРИНЫ: 
                        # Если 13+ — летим сразу. Если 10-12, но по факту долбили много (блоки + мимо) — зовем ИИ.
                        if (on_g >= 13 or (on_g >= 10 and total_att >= 17)) and pens >= 2:
                            home, away = ev['homeTeam']['shortName'], ev['awayTeam']['shortName']
                            verdict = await ai_decision(home, away, f"{h_p1}:{a_p1}", s_map)
                            
                            if "ЗАХОДИМ" in verdict.upper():
                                msg = (
                                    f"🚨 <b>СИГНАЛ: {home} — {away}</b>\n"
                                    f"🥅 Счет P1: <b>{h_p1}:{a_p1}</b>\n"
                                    f"🎯 В створ: <b>{on_g}</b> | ⏳ Штраф: <b>{pens}м</b>\n"
                                    f"🏒 Общая активность: <b>{total_att}</b>\n"
                                    f"━━━━━━━━━━━━━━━━━━\n"
                                    f"🤖 <b>AI ВЕРДИКТ:</b> {verdict.strip()}"
                                )
                                await session.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                                 json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})
                                SENT_SIGNALS.add(mid)

            except Exception as e: print(f"Error: {e}")
            await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(main())
