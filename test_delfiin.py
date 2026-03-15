import requests, json

# Смотрим что грузит страница поиска Delfiin
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/html, */*",
    "Referer": "https://www.delfiin.ee/",
})

# Пробуем загрузить страницу напрямую
r = session.get("https://www.delfiin.ee/ru/sooduspakkumised/1773705600/#17031007", timeout=20)
print("HTTP:", r.status_code)
print("Content-Type:", r.headers.get("content-type", ""))
print("Первые 1000 символов:")
print(r.text[:1000])
