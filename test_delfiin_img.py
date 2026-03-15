import requests
from bs4 import BeautifulSoup

r = requests.get(
    "https://www.delfiin.ee/showhotel.php?e=a2ZXYWNDWWl3RW5BQmRHS1VCbHh3Zz09&l=1",
    timeout=10,
    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
)
soup = BeautifulSoup(r.text, "html.parser")

# Все img теги
imgs = soup.find_all("img")
print(f"Всего img: {len(imgs)}")
for img in imgs[:10]:
    print(f"  src={img.get('src','')[:100]}  w={img.get('width','')}  h={img.get('height','')}")
