import asyncio
import aiohttp
from datetime import datetime, timedelta

# --- ОБЯЗАТЕЛЬНО ПРОВЕРЬ ЭТИ ДАННЫЕ ---
TOKEN = "ТВОЙ_ТОКЕН_БОТА"
CHAT_ID = "ТВОЙ_CHAT_ID"

async def send_tg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
        try:
            async with session.post(url, json=payload, timeout=10) as r:
                res = await r.json()
                if not res.get('ok'):
                    print(f"❌ Ошибка Telegram API: {res.get('description')}", flush=True)
                return res
        except Exception as e:
            print(f"❌ Ошибка сети при отправке в ТГ: {e}", flush=True)

async def check_league(session, event_ids):
    # Проверяем до 5 матчей, чтобы точно не пропустить статистику
    for mid in event_ids[:5]:
        try:
            url = f"https://api.sofascore.com/api/v1/event/{mid}/statistics"
            async with session.get(url, timeout=7) as r:
                if r.status != 200: continue
                data = await r.json()
                stats = data.get('statistics', [])
                target = next((p for p in stats if p.get('period') == 'ALL'), None)
                if not target: continue
                
                has_s, has_p = False, False
                for group in target.get('groups', []):
                    for item in group.get('statisticsItems', []):
                        key = str(item.get('key', '')).lower()
                        name = str(item.get('name', '')).lower()
                        # Наша "собака" и штрафы
                        if key in ['shots', 'shotsongoal'] or 'створ' in name: has_s = True
                        if 'penalty' in key or 'штраф' in name: has_p = True
                
                if has_s and has_p: return True
        except: continue
    return False

async def main():
    print("--- 🛰 ЗАПУСК v150.0 ---", flush=True)
    await send_tg("🚀 <b>Бот запущен.</b> Начинаю глубокий анализ за 3 дня...")

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    white_list = set()
    days = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(3)]

    async with aiohttp.ClientSession(headers=headers) as session:
        for date in days:
            print(f"📅 Проверка даты: {date}", flush=True)
            try:
                url = f"https://api.sofascore.com/api/v1/sport/ice-hockey/scheduled-events/{date}"
                async with session.get(url, timeout=15) as r:
                    if r.status != 200: continue
                    events = (await r.json()).get('events', [])
                    
                    leagues = {}
                    for ev in events:
                        n = ev.get('tournament', {}).get('name', 'Unknown')
                        if n not in leagues: leagues[n] = []
                        leagues[n].append(ev.get('id'))
                    
                    for l_name, ids in leagues.items():
                        if l_name in white_list: continue
                        if await check_league(session, ids):
                            white_list.add(l_name)
                            print(f"➕ Добавлена: {l_name}", flush=True)
                        await asyncio.sleep(0.1)
            except Exception as e:
                print(f"⚠ Ошибка на дате {date}: {e}", flush=True)

    # Итоговый отчет
    if white_list:
        res_text = "<b>✅ БЕЛЫЙ СПИСОК ГОТОВ:</b>\n\n" + "\n".join([f"• <code>{l}</code>" for l in sorted(white_list)])
    else:
        res_text = "⚠️ <b>Анализ завершен.</b> Лиг со статистикой не найдено."
    
    await send_tg(res_text)
    print("🏁 Отчет отправлен в ТГ.", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
