"""
images.py — получение картинок отелей через Booking.com
Использует открытый endpoint поиска, без авторизации.
Результаты кэшируются в БД (таблица hotel_images).
"""
import logging
import re

logger = logging.getLogger(__name__)


def get_hotel_image(hotel_name: str, destination: str = "Egypt") -> str:
    """
    Ищет картинку отеля на Booking.com по названию.
    Возвращает URL картинки или пустую строку.
    Кэш в БД по ключу "booking:{hotel_name}".
    """
    try:
        from database import get_cached_image, cache_image
    except ImportError:
        return ""

    cache_key = f"booking:{hotel_name.lower().strip()}"

    cached = get_cached_image(cache_key)
    if cached is not None:
        return cached

    try:
        import requests
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ru,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        })

        query = f"{hotel_name} {destination}"
        search_url = "https://www.booking.com/searchresults.ru.html"
        resp = session.get(search_url, params={"ss": query, "rows": "5"}, timeout=15)

        if resp.status_code != 200:
            cache_image(cache_key, "")
            return ""

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        image_url = ""

        # Ищем первую карточку отеля с картинкой
        for img in soup.find_all("img", src=True):
            src = img.get("src", "") or img.get("data-src", "")
            if not src:
                continue
            # Booking хранит картинки на cf.bstatic.com или bstatic.com
            if "bstatic.com" in src and "/hotel" in src:
                # Увеличиваем размер картинки: меняем размер в URL
                src = re.sub(r'max\d+', 'max500', src)
                src = re.sub(r'square\d+', 'square500', src)
                image_url = src
                break

        # Fallback: ищем в data-src атрибутах
        if not image_url:
            for tag in soup.find_all(attrs={"data-src": True}):
                src = tag.get("data-src", "")
                if "bstatic.com" in src and "/hotel" in src:
                    image_url = re.sub(r'max\d+', 'max500', src)
                    break

        cache_image(cache_key, image_url)
        logger.debug(f"Booking image for '{hotel_name}': {image_url[:60] if image_url else 'not found'}")
        return image_url

    except Exception as e:
        logger.debug(f"Booking image error for '{hotel_name}': {e}")
        cache_image(cache_key, "")
        return ""
