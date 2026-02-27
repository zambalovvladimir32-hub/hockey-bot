import asyncio
import aiohttp
import os
import logging
import sys
from google import genai
from aiogram import Bot

# Настройка логов для Amvera
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(message)s', 
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Данные из переменных окружения
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

bot = Bot(token=TOKEN)
client = genai.Client(api_key=GEMINI_KEY)

# URL изменен на универсальный (тянет все лиги: ВХЛ, КХЛ, НХЛ и т.д.)
URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/0"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

sent_signals = set()

async def get_ai_prediction(match_data, algo):
    """Запрос аналитики у Gemini"""
    try:
        prompt = f"Ты хоккейный эксперт. Стратегия: {algo}. Матч: {match_data}. Дай прогноз на остаток периода (до 7 слов)."
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        return f"🤖 AI: {response.text.strip()}"
    except Exception as e:
        logger.error(f"Ошибка Gemini: {e}")
        return "🤖 AI: Ожидается активная игра в зоне атаки."

async def check_logic():
    logger.info("--- СКАНИРОВАНИЕ ЛИНИИ (ВСЕ ЛИГИ) ---")
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(URL, timeout=15) as resp:
                if resp.status != 200:
                    logger.error(f"Ошибка доступа к API: {resp.status}")
                    return
                
                data = await resp.json()
                found_any_match = False
                
                for stage in data.get('Stages', []):
                    # Название лиги и страны для логов
                    country = stage.get('Cnm', '')
                    league = stage.get('Snm', '')
                    
                    for event in stage.get('Events', []):
                        found_any_match = True
                        eid = event.get('Eid')
                        t1 = event['T1'][0]['Nm']
                        t2 = event['T2'][0]['Nm']
                        period = event.get('Eps') # '1ST', '2ND', '3RD'
                        
                        try:
                            # Минуты и счет
                            m = int(event.get('Emm', 0))
                            s1 = int(event.get('Tr1', 0))
                            s2 = int(event.get('Tr2', 0))
                        except (ValueError, TypeError):
                            continue

                        # ЛОГИРОВАНИЕ: Пишем в консоль всё, что видим в 1-м и 2-м периодах
                        if period in ['1ST', '2ND']:
                            logger.info(f"Матч: {t1}-{t2} | {period} | {m} мин | Счет {s1}:{s2} ({league})")

                        # --- АЛГОРИТМЫ ---
                        algo = None
                        
                        # 1. Засуха в 1-м периоде (расширил до 11-19 минут)
                        if period == '1ST' and 11 <= m <= 19 and (s1 + s2 <= 1):
                            algo = "💎 ЗАСУХА (1-й ПЕР)"
                            
                        # 2. Тотал во 2-м периоде (активность 21-35 мин)
                        elif period == '2ND' and 21 <= m <= 35 and (s1 + s2 < 5):
                            algo = "🔥 ТОТАЛ (2-й ПЕР)"
                        
                        # 3. Камбэк (разница в 2 шайбы во 2-м периоде)
                        elif period == '2ND' and abs(s1 - s2) >= 2 and (s1 + s2 < 6):
                            algo = "🧨 ОЖИДАЕМ КАМБЭК"

                        if algo:
                            key = f"{eid}_{algo}"
                            if key not in sent_signals:
                                logger.info(f"!!! СРАБОТАЛ СИГНАЛ: {t1}-{t2} !!!")
                                
                                # Анализ ИИ
                                ai_text = await get_ai_prediction(f"{t1}-{t2} (Счет {s1}:{s2})", algo)
                                
                                # Сообщение
                                msg = (
                                    f"🚨 **{algo}**\n"
                                    f"🏒 **{t1} — {t2}**\n"
                                    f"📊 Счет: `{s1}:{s2}` ({m} мин)\n"
                                    f"🏆 {league}\n\n"
                                    f"{ai_text}"
                                )
                                
                                try:
                                    await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                    sent_signals.add(key)
                                    logger.info(f"Успешно отправлено в ТГ")
                                except Exception as e:
                                    logger.error(f"Ошибка отправки в ТГ: {e}")

                if not found_any_match:
                    logger.info("Матчей в Live сейчас нет.")
                                
        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}")

async def main():
    # Тест связи при старте
    try:
        await bot.send_message(CHANNEL_ID, "✅ Бот переведен в БОЕВОЙ РЕЖИМ. Сканирую все лиги (ВХЛ, КХЛ, NHL).")
        logger.info("Тестовое сообщение отправлено.")
    except Exception as e:
        logger.error(f"Ошибка связи с ТГ: {e}")

    while True:
        await check_logic()
        await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(main())
