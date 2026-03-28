import requests
from bs4 import BeautifulSoup
s = requests.Session()
s.headers.update({'User-Agent':'Mozilla/5.0','Accept-Language':'ru-RU,ru;q=0.9'})
r = s.get('https://www.delfiin.ee/hoteldesc.php?e=WHAra210N1Y0NEYyb2kyemE5aytCQT09&l=1&r')
print('status:', r.status_code)
soup = BeautifulSoup(r.text, 'html.parser')
imgs = [i.get('src','') for i in soup.find_all('img', src=True)]
print(imgs[:10])
