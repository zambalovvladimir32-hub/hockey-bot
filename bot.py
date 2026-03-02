import asyncio, os, logging, re
from aiogram import Bot
from curl_cffi.requests import AsyncSession
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeyHybrid_v56.0")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

class HockeyFinal:
    def __init__(self):
        self.sent_cache = {}
        self.flash_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo", 
            "X-Referer": "https://www.flashscore.ru/"
        }
        self.sofa_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        # Словарь для критических матчей (белорусская/российская лиги)
        self.translate_map = {
            "Витебск": "Vitebsk", "Гомель": "Gomel", "Неман Гродно": "Neman Grodno",
            "Металлург-Жлобин": "Metallurg Zhlobin", "Локомотив Орша": "Lokomotiv Orsha",
            "Динамо Молодечно": "Dinamo Molodechno", "Брест": "Brest", "Шахтер Солигорск": "Shakhter Soligorsk"
        }

    async def get_sofa_stats(self, session, h_team, a_team):
        """Умный поиск на SofaScore с поддержкой перевода"""
        try:
            # 1. Очистка и перевод
            h_search = self.translate_map.get(h_team, re.sub(r'\(.*?\)', '', h_team).strip())
            
            # 2. Поиск ID матча
            q = quote(h_search)
            search_url = f"https://www.sofascore.com/api/v1/search/all?q={q}"
            r = await session.get(search_url, headers=self.sofa_headers, impersonate="chrome110")
            
            if r.status_code != 200: return None
            
            data = r.json()
            event_id = None
            for res in data.get('results', []):
                if res.get('type') == 'event' and res.get('entity', {}).get('sport', {}).get('slug') == 'ice-hockey':
                    # Проверка на LIVE статус или недавний старт
                    event_id = res['entity']['id']
                    break
            
            if not event_id: return None

            # 3. Запрос статистики
            stat_url = f"https://www.sofascore.com/api/v1/event/{event_id}/statistics"
            r_stat = await session.get(stat_url, headers=self.sofa_headers, impersonate="chrome110")
            
            if r_stat.status_code == 200:
                s_data = r_stat.json()
                res = {"shots": 0, "pen": 0}
                for period in s_data.get('statistics', []):
                    if period.get('period') == 'ALL':
                        for group in period.get('groups', []):
                            for item in group.get('statisticsItems', []):
                                if 'Shots on goal' in item['name']:
                                    res['shots'] = int(item['homeValue']) + int(item['awayValue'])
                                if 'Penalty minutes' in item['name']:
                                    res['pen'] = int(item['homeValue']) + int(item['awayValue'])
                return res
        except: return None

    async def run(self):
        logger.info("🚀 v56.0 В РАБОТЕ: Flashscore + SofaScore + AutoTranslate")
        async with AsyncSession() as session:
            while True:
                try:
                    # Flashscore мониторинг
                    url = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
                    r = await session.get(url, headers=self.flash_headers, impersonate="chrome110")
                    
                    if r.status_code == 200 and "¬" in r.text:
                        matches = [m for m in r.text.split('~AA÷')[1:] if "AC÷46" in m]
                        
                        for m_block in matches:
                            m_id = m_block.split('¬')[0]
                            if m_id in self.sent_cache: continue

                            h_score = int(m_block.split('AG÷')[1].split('¬')[0])
                            a_score = int(m_block.split('AH÷')[1].split('¬')[0])

                            if (h_score + a_score) <= 1:
                                h_name = m_block.split('AE÷')[1].split('¬')[0]
                                a_name = m_block.split('AF÷')[1].split('¬')[0]
                                
                                logger.info(f"📊 Нашел перерыв {h_name}. Запрашиваю статику...")
                                stats = await self.get_sofa_stats(session, h_name, a_name)
                                
                                if stats:
                                    logger.info(f"✅ Статистика {h_name} получена: {stats['shots']} бросков")
                                    if stats['shots'] >= 11 or stats['pen'] >= 4:
                                        msg = (f"🏒 **{h_name} {h_score}:{a_score} {a_name}**\n"
                                               f"🎯 Броски: `{stats['shots']}` | ⚖️ Штраф: `{stats['pen']} мин`")
                                        await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                        self.sent_cache[m_id] = True
                                        logger.info(f"💰 Сигнал отправлен!")

                    await asyncio.sleep(120)
                except Exception as e:
                    logger.error(f"Error: {e}")
                    await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(HockeyFinal().run())
