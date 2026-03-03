import asyncio
import aiohttp
import os

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")

WHITE_LIST = [
    "KHL", "NHL", "National Hockey League", "SHL", "Liiga", 
    "DEL", "Extraliga", "Tipsport Liga", "ICE Hockey League", "1st Liga"
]

SENT_SIGNALS = set()

async def send_tg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
        await session.post(url, json=payload)

async def get_stats(session, mid):
    """Строгий парсинг статы за 1-й период (БЕЗ ПЕРЕЗАПИСИ)"""
    try:
        url = f"https://api.sofascore.com/api/v1/event/{mid}/statistics"
        async with session.get(url, timeout=5) as r:
            if r.status != 200: return None
            data = await r.json()
            p1 = next((p for p in data.get('statistics', []) if p.get('period') == '1ST'), None)
            if not p1: return None

            shots, penalties = 0, 0
            for group in p1.get('groups', []):
                for item in group.get('statisticsItems', []):
                    key = str(item.get('key', '')).lower()
                    h, a = int(item.get('homeValue', 0)), int(item.get('awayValue', 0))
                    
                    # СТРОГОЕ СОВПАДЕНИЕ (никаких блокированных бросков)
                    if key in ['shotsongoal', 'shots']:
                        shots = h + a
                    # СТРОГОЕ СОВПАДЕНИЕ ШТРАФОВ
                    if key in ['penaltyminutes', 'penalty']:
                        penalties = h + a
            return shots, penalties
    except: return None

async def main():
    print("--- 🎯 СНАЙПЕР v162.0: ИСПРАВЛЕН БАГ СТАТИСТИКИ ---", flush=True)
    await send_tg("🛠 <b>Обновление v162.0.</b> Баг сброса статистики устранен. Жду перерывы...")

    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        while True:
            try:
                async with session.get("https://api.sofascore.com/api/v1/sport/ice-hockey/events/live") as r:
                    if r.status != 200: continue
                    events = (await r.json()).get('events', [])

                for ev in events:
                    mid = ev.get('id')
                    if mid in SENT_SIGNALS: continue

                    # 1. Лига
                    l_name = ev.get('tournament', {}).get('name', '')
                    if not any(t.upper() in l_name.upper() for t in WHITE_LIST): continue

                    # 2. Статус 31 (Перерыв)
                    if ev.get('status', {}).get('code', 0) != 31: continue

                    # 3. Счет (0:0, 1:0, 0:1)
                    h_p1 = ev.get('homeScore', {}).get('period1', 0)
                    a_p1 = ev.get('awayScore', {}).get('period1', 0)
                    if (h_p1 + a_p1) <= 1:
                        
                        # 4. Статистика
                        stats = await get_stats(session, mid)
                        if stats:
                            shots, penalties = stats
                            if shots >= 13 and penalties >= 2:
                                home = ev['homeTeam']['shortName']
                                away = ev['awayTeam']['shortName']
                                
                                msg = (
                                    f"🚨 <b>СИГНАЛ: ПЕРЕРЫВ 1-го ПЕРИОДА</b>\n\n"
                                    f"🏆 {l_name}\n"
                                    f"🤝 <b>{home} — {away}</b>\n"
                                    f"━━━━━━━━━━━━━━━━━━\n"
                                    f"🥅 Счет 1-го пер.: <b>{h_p1}:{a_p1}</b>\n"
                                    f"🎯 Удары в створ: <b>{shots}</b>\n"
                                    f"⏳ Штраф: <b>{penalties} мин</b>\n"
                                    f"━━━━━━━━━━━━━━━━━━\n"
                                    f"✅ Условия соблюдены!"
                                )
                                await send_tg(msg)
                                SENT_SIGNALS.add(mid)

            except Exception as e:
                print(f"⚠ Ошибка: {e}", flush=True)
            
            await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(main())
