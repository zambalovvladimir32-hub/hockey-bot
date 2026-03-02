import asyncio
import aiohttp
from datetime import datetime, timedelta

# --- НАСТРОЙКИ ТГ ---
TOKEN = "ТВОЙ_ТОКЕН"
CHAT_ID = "ТВОЙ_CHAT_ID"

async def send_tg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
        await session.post(url, json=payload)

async def validate_league_stats(session, event_ids):
    """Проверяет матчи лиги. Нужно чтобы и удары, и штрафы были > 0"""
    for mid in event_ids[:3]: # Проверяем до 3-х матчей для надежности
        try:
            url = f"https://api.sofascore.com/api/v1/event/{mid}/statistics"
            async with session.get(url, timeout=5) as r:
                if r.status != 200: continue
                data = await r.json()
                periods = data.get('statistics', [])
                if not periods: continue
                
                target = next((p for p in periods if p.get('period') == 'ALL'), periods[0])
                has_s, has_p = False, False
                
                for group in target.get('groups', []):
                    for item in group.get('statisticsItems', []):
                        key = str(item.get('key', '')).lower()
                        name = str(item.get('name', '')).lower()
                        
                        # Ищем те самые ключи, что мы "прижали" ранее
                        if key == 'shots' or key == 'shotsongoal' or 'створ' in name:
                            has_s = True
                        if 'penalty' in key or 'штраф' in name:
                            has_p = True
                
                if has_s and has_p: return True # Лига прошла проверку
        except: continue
    return False

async def main():
    headers = {"User-Agent": "Mozilla/5.0"}
    white_list = set()
    days = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(3)]

    async with aiohttp.ClientSession(headers=headers) as session:
        await send_tg("🛠 <b>Запуск фильтрации...</b>\nАнализирую лиги за 3 дня на наличие ударов и штрафов.")
        
        for date in days:
            url = f"https://api.sofascore.com/api/v1/sport/ice-hockey/scheduled-events/{date}"
            async with session.get(url) as r:
                if r.status != 200: continue
                events = (await r.json()).get('events', [])
                
                # Группируем матчи по лигам
                leagues_map = {}
                for ev in events:
                    l_full = ev.get('tournament', {}).get('name', '')
                    if l_full not in leagues_map: leagues_map[l_full] = []
                    leagues_map[l_full].append(ev.get('id'))

                # Фильтруем каждую лигу
                for l_name, ids in leagues_map.items():
                    if l_name in white_list: continue
                    if await validate_league_stats(session, ids):
                        white_list.add(l_name)
                    await asyncio.sleep(0.3) # Чтобы Railway не забанили

        if white_list:
            # Формируем список в столбик для удобного копирования
            msg = "<b>✅ ПОЛНЫЙ БЕЛЫЙ СПИСОК:</b>\n\n"
            msg += "\n".join([f"<code>{l}</code>" for l in sorted(white_list)])
            msg += f"\n\n<i>Всего: {len(white_list)} лиг со статистикой.</i>"
        else:
            msg = "❌ Лиг с полной статистикой не обнаружено."
        
        await send_tg(msg)

if __name__ == "__main__":
    asyncio.run(main())
