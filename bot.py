import asyncio
import aiohttp
import os
import logging
from aiogram import Bot
from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Твои ключи
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=TOKEN)
gpt_client = AsyncOpenAI(api_key=OPENAI_KEY)

# ТОТ САМЫЙ РАБОЧИЙ АДРЕС (код 200)
URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/8"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}

sent_signals = set()

async def get_ai_analysis(match):
    try:
        res = await gpt_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": f"Хоккей. {match}. Вероятность ТБ 4.5. Вердикт до 12 слов."}],
            max_tokens=50
        )
        return res.choices[0].message.content
    except: return "Статистика указывает на высокую результативность."

async def check_hockey():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(URL, timeout=15) as resp:
                if resp.status != 200: return
                
                data = await resp.json()
                for stage in data.get('Stages', []):
                    league = stage.get('Snm', '').upper()
                    
                    # Фильтр твоих лиг (КХЛ, ВХЛ, Казахстан)
                    target = ['KHL', 'VHL', 'KAZAKHSTAN', 'MHL', 'RUSSIA']
                    if not any(x in league for x in target): continue
                    
                    for event in stage.get('Events', []):
                        eid = event.get('Eid')
                        if eid in sent_signals: continue
                        
                        h_score = int(event.get('Tr1', 0))
                        a_score = int(event.get('Tr2', 0))
                        status = event.get('Eps', '').upper()
                        
                        # УСЛОВИЯ: 1-й период или 2-й период 0:0
                        is_p1 = '1ST' in status
                        is_p2_zero = '2ND' in status and (h_score + a_score == 0)
                        
                        if is_p1 or is_p2_zero:
                            home = event.get('T1', [{}])[0].get('Nm')
                            away = event.get('T2', [{}])[0].get('Nm')
                            match_info = f"{home} — {away}, счет {h_score}:{a_score}"
                            
                            analysis = await get_ai_analysis(match_info)
                            
                            msg = (f"🏒 **СИГНАЛ: {league}**\n\n"
                                   f"⚔️ **{home} — {away}**\n"
                                   f"📊 Счет: `{h_score}:{a_score}`\n"
                                   f"⏱ Статус: `{status}`\n\n"
                                   f"🤖 **ИИ:** {analysis}")
                            
                            await bot.send_message(CHANNEL_ID, msg)
                            sent_signals.add(eid)
                            logger.info(f"Сигнал: {home}")
        except Exception as e:
            logger.error(f"Ошибка: {e}")

async def main():
    logger.info("Бот запущен!")
    await bot.send_message(CHANNEL_ID, "✅ **Бот запущен! Прямой канал связи установлен.**\nМониторинг КХЛ и ВХЛ активен.")
    while True:
        await check_hockey()
        await asyncio.sleep(120)

if __name__ == "__main__":
    asyncio.run(main())
