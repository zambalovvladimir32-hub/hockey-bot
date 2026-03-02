import asyncio, os, logging, re
from aiogram import Bot
from curl_cffi.requests import AsyncSession
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeyTEST_v55.3")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

class HockeyTest:
    def __init__(self):
        # Заголовки для обхода 401 ошибки Flashscore
        self.flash_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo", 
            "X-Referer": "https://www.flashscore.ru/",
            "Accept": "*/*"
        }
        self.sofa_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

    async def run_test(self):
        logger.info("🧪 ЗАПУСК ТЕСТА: Проверяем связку Flashscore + SofaScore...")
        async with AsyncSession() as session:
            # 1. Стучимся во Flashscore за списком
            url = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
            r = await session.get(url, headers=self.flash_headers, impersonate="chrome110")
            
            if r.status_code != 200:
                logger.error(f"❌ Flashscore не пустил! Статус: {r.status_code}")
                return

            # Берем первые 3 матча из списка (любые)
            matches = r.text.split('~AA÷')[1:4]
            logger.info(f"🔎 Взял {len(matches)} матча из списка для теста.")

            for m_block in matches:
                h_team = m_block.split('AE÷')[1].split('¬')[0]
                a_team = m_block.split('AF÷')[1].split('¬')[0]
                
                logger.info(f"🎲 Пробую найти на SofaScore: {h_team} - {a_team}")
                
                # Чистим названия для SofaScore
                clean_h = re.sub(r'\(.*?\)', '', h_team).strip()
                clean_a = re.sub(r'\(.*?\)', '', a_team).strip()

                # Поиск на SofaScore
                q = quote(f"{clean_h} {clean_a}")
                search_url = f"https://www.sofascore.com/api/v1/search/all?q={q}"
                r_search = await session.get(search_url, headers=self.sofa_headers, impersonate="chrome110")
                
                if r_search.status_code == 200:
                    data = r_search.json()
                    event_id = next((res['entity']['id'] for res in data.get('results', []) 
                                    if res.get('type') == 'event' and 
                                    res.get('entity', {}).get('sport', {}).get('slug') == 'ice-hockey'), None)
                    
                    if event_id:
                        logger.info(f"✅ Матч найден! ID: {event_id}. Тяну статистику...")
                        # Запрос статистики
                        s_url = f"https://www.sofascore.com/api/v1/event/{event_id}/statistics"
                        r_stat = await session.get(s_url, headers=self.sofa_headers, impersonate="chrome110")
                        
                        if r_stat.status_code == 200:
                            s_data = r_stat.json()
                            logger.info(f"📊 СТАТИСТИКА ПОЛУЧЕНА ДЛЯ {h_team}!")
                            # Отправляем в ТГ для подтверждения успеха
                            await bot.send_message(CHANNEL_ID, f"🧪 ТЕСТ УСПЕШЕН:\n🏒 {h_team} vs {a_team}\n✅ Связка Flash+Sofa работает!")
                        else:
                            logger.warning(f"⚠️ Статистика для {event_id} пока недоступна (матч может быть в будущем)")
                    else:
                        logger.warning(f"❌ SofaScore не нашел матч: {clean_h}")
                else:
                    logger.error(f"❌ Ошибка поиска Sofa: {r_search.status_code}")

if __name__ == "__main__":
    asyncio.run(HockeyTest().run_test())
