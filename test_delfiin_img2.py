from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

url = "https://www.delfiin.ee/hoteldesc.php?e=M0IwT2UvT3hTOXdZNTBwdGxpQXFEZz09&l=0&r#"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    ).new_page()
    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)
    html = page.content()
    browser.close()

soup = BeautifulSoup(html, "html.parser")
imgs = soup.find_all("img")
print(f"Всего img: {len(imgs)}")
for img in imgs[:10]:
    print(f"  src={img.get('src','')[:120]}")
