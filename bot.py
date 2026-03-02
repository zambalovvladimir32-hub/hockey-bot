import asyncio, os, logging, re
from aiogram import Bot
from curl_cffi.requests import AsyncSession
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeyTEST_v49.1")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ZENROWS_TOKEN = os.getenv("ZENROWS_TOKEN") 

bot = Bot(token=TOKEN)

class HockeyLogic:
    async def fetch_flashscore(self, session):
        url = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        # Используем ZenRows для обхода блока списка
        api_url = f"https://api.zenrows.com/v1/?apikey={ZENROWS_TOKEN}&url={quote(url)}&premium_proxy=true"
        try:
            r = await session.get(api_url, timeout=30)
            return r.text if r.status_code == 200 else None
        except Exception as e:
            logger.error(f"Flashscore error: {e}")
            return None

    async def get_sofascore_stats(self, session, h_name, a_name):
        try:
            # 1. Поиск матча
            search_query = quote(f"{h_name} {a_name}")
            search_url = f"https://www.sofascore.com/api/v1/search/all?q={search_query}"
            headers = {"User-Agent": "Mozilla/5.0"}
            
            r_search = await session.get(search_url, headers=headers)
            if r_search.status_code != 200: 
                logger.warning(f"SofaSearch status: {r_search.status_code}")
                return None
            
            data = r_search.json()
            event_id = None
            for res in data.get('results', []):
                if res.get('type') == 'event' and res.get('entity', {}).get('sport', {}).get('slug') == 'ice-hockey':
                    event_id = res['entity']['id']
                    break
            
            if not event_id:
                logger.warning(f"❌ Матч {h_name} не найден на SofaScore")
                return None

            # 2. Статистика
            stat_url = f"https://www.sofascore.com/api/v1/event/{event_id}/statistics"
            r_stat = await session.get(stat_url, headers=headers)
            
            if r_stat.status_code == 200:
                stats_data = r_stat.json()
                res = {"shots": 0, "pen": 0}
                # Парсим JSON (SofaScore отдает структуру по периодам или ALL)
                for stat_group in stats_data.get('statistics', []):
                    if stat_group.get('period') == 'ALL':
                        for group in stat_group.get('groups', []):
                            for item in group.get('statisticsItems', []):
                                if 'Shots on goal' in item['name']:
                                    res['shots'] = int(item['homeValue']) + int(item['awayValue'])
                                if 'Penalty minutes' in item['name']:
                                    res['pen'] = int(item['homeValue']) + int(item['awayValue'])
                return res
            return None
        except Exception as e:
            logger.error(f"SofaStat error: {e}")
            return None

    async def run(self):
        logger.info("🧪 ТЕСТОВЫЙ ЗАПУСК v49.1: ПРОВЕРКА СВЯЗКИ API")
        async with AsyncSession() as session:
            list_data = await self.fetch_flashscore(session)
            if list_data and "¬" in list_data:
                # Берем первые 3 любых матча из списка для теста
                matches = list_data.split('~AA÷')[1:4]
                logger.info(f"🔎 Взял {len(matches)} матча для теста...")

                for m_block in matches:
                    h_name = m_block.split('AE÷')[1].split('¬')[0]
                    a_name = m_block.split('AF÷')[1].split('¬')[0]
                    
                    logger.info(f"🎲 Тестирую: {h_name} vs {a_name}")
                    
                    # Очистка названия для поиска
                    clean_h = re.sub(r'\(.*?\)', '', h_name).strip()
                    clean_a = re.sub(r'\(.*?\)', '', a_name).strip()
                    
                    res = await self.get_sofascore_stats(session, clean_h, clean_a)
                    
                    if res:
                        logger.info(f"✅ УСПЕХ! Найдено на SofaScore. Броски: {res['shots']}, Штраф: {res['pen']}")
                        # Отправим тестовое сообщение, чтобы проверить и Телеграм
                        await bot.send_message(CHANNEL_ID, f"🧪 ТЕСТ СВЯЗКИ:\n🏒 {h_name} - {a_name}\n🎯 Броски: {res['shots']}")
                    else:
                        logger.warning(f"⚠️ Для матча {h_name} статика не получена (возможно, еще нет данных)")
            else:
                logger.error("❌ Не удалось получить список матчей с Flashscore. Проверь ZenRows!")

if __name__ == "__main__":
    asyncio.run(HockeyLogic().run())
