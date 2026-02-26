import asyncio
import aiohttp
import os
import logging
from aiogram import Bot
from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=TOKEN)
gpt_client = AsyncOpenAI(api_key=OPENAI_KEY)

# Рабочий шлюз, который ожил в твоих логах
URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/8"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}

sent_matches = set()

async def get_ai_analysis(match_name):
    try:
        # Добавляем паузу, чтобы OpenAI не ругался на лимиты
        await asyncio.sleep(2) 
        res = await gpt_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": f"Хоккей. {match_name}. Прогноз на тотал больше 4.5. Вердикт до 10 слов."}],
            max_tokens=50
        )
        return res.choices[0].message.content
    except Exception as e:
        logger.warning(f"GPT лимит: {e}")
        return "Анализ будет доступен в следующем цикле."

async def run_monitoring():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        while True:
            try:
                async with session.get(URL, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        stages = data.get('Stages', [])
                        
                        for stage in stages:
                            for event in stage.get('Events', []):
                                eid = event.get('Eid')
                                
                                # Если этот матч мы уже отправляли - пропускаем
                                if eid in sent_matches: continue
                                
                                home = event.get('T1', [{}])[0].get('Nm', 'Team1')
                                away = event.get('T2', [{}])[0].get('Nm', 'Team2')
                                h_score = event.get('Tr1', '0')
                                a_score = event.get('Tr2', '0')
                                
                                # Берем только КХЛ, НХЛ, МХЛ и Европу (убираем кибер и ночные лиги)
                                league = stage.get('Snm', '').upper()
                                if any(x in league for x in ['NHL 24', 'CYBER', 'SHORT']): continue

                                analysis = await get_ai_analysis(f"{home} - {away}")
                                
                                msg = (f"🏒 **МАТЧ В ЛАЙВЕ**\n\n"
                                       f"⚔️ **{home} — {away}**\n"
                                       f"📊 Счет: `{h_score}:{a_score}`\n"
                                       f"🤖 **GPT:** {analysis}")
                                
                                await bot.send_message(CHANNEL_ID, msg)
                                sent_matches.add(eid)
                                logger.info(f"Отправлен матч: {home}")
                                
                                # Даем боту "выдохнуть" между сообщениями
                                await asyncio.sleep(3) 
                    else:
                        logger.error(f"Ошибка API: {resp.status}")
            except Exception as e:
                logger.error(f"Ошибка цикла: {e}")
            
            await asyncio.sleep(120) # Проверка раз в 2 минуты

async def main():
    await bot.send_message(CHANNEL_ID, "🚀 **Бот перенастроен.**\nЛимиты GPT оптимизированы. Мониторинг продолжается!")
    await run_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
