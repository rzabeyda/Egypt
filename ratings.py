# Рейтинги отелей из канала @egypthotelz
# Формат: "ключевое слово в нижнем регистре": рейтинг (float)

HOTEL_RATINGS = {
    "barcelo tiran sharm":       7.9,
    "barceló tiran sharm":       7.9,
    "pickalbatros luxury suites":9.5,
    "jaz neo naama bay":         8.6,
    "jaz neo sharks bay":        8.8,
    "hawaii riviera":            7.6,
    "minamark":                  7.6,
    "regency plaza":             7.8,
    "panorama naama":            7.8,
    "amphoras aqua":             7.8,
    "empire beach":              7.8,
    "le pacha":                  7.8,
    "oonas dive":                7.9,
    "jaz aquaviva":              7.9,
    "amphoras blu":              7.9,
    "naama blue":                8.0,
    "marlin inn azur":           8.1,
    "tropitel dahab":            8.1,
    "shores amphoras":           8.1,
    "sharm holiday":             8.2,
    "il mercato":                8.2,
    "steigenberger aqua":        8.2,
    "jaz sharks bay":            8.3,
    "giftun azur":               8.3,
    "domina coral bay":          8.4,
    "cleopatra luxury":          8.4,
    "reef oasis blue bay":       8.4,
    "alf leila":                 8.4,
    "albatros citadel":          8.5,
    "coral sea holiday":         8.5,
    "tropitel sahl":             8.6,
    "hilton sharks bay":         8.6,
    "concorde el salam":         8.6,
    "ali baba palace":           8.6,
    "mirage bay":                8.7,
    "beach albatros sharm":      8.7,
    "coral sea waterworld":      8.7,
    "camel dive":                8.7,
    "meraki resort":             8.7,
    "sentido reef":              8.7,
    "charmillion":               8.7,
    "hilton hurghada plaza":     8.7,
    "desert rose":               8.7,
    "swissôtel sharm":           8.7,
    "swissotel sharm":           8.7,
    "steigenberger golf":        8.7,
    "hilton marsa alam":         8.8,
    "titanic resort":            8.8,
    "jaz sharm dreams":          8.8,
    "albatros palace":           8.8,
    "pickalbatros jungle":       8.8,
    "pickalbatros white beach":  8.8,
    "reef oasis beach":          8.8,
    "sultan gardens resort":     8.8,
    "grand rotana":              8.9,
    "hyatt regency sharm":       8.9,
    "titanic beach spa":         8.9,
    "pickalbatros water valley": 8.9,
    "pickalbatros aqua park":    8.9,
    "monte carlo sharm":         8.9,
    "jaz aquamarine":            8.9,
    "jaz fanara":                9.0,
    "jaz mirabel":               9.0,
    "pickalbatros laguna vista": 9.0,
    "titanic palace":            9.0,
    "rixos premium seagate":     9.0,
    "sunrise holidays resort":   9.0,
    "sunrise royal makadi":      9.0,
    "baron palms":               9.0,
    "baron resort sharm":        9.1,
    "sultan gardens":            9.1,
    "savoy sharm":               9.1,
    "savoy royal":               9.1,
    "titanic royal":             9.1,
    "steigenberger aldau":       9.1,
    "sunrise diamond":           9.1,
    "jaz belvedere":             9.2,
    "premier le reve":           9.2,
    "sunrise arabian beach":     9.2,
    "rixos premium magawish":    9.2,
    "rixos radamis":             9.2,
    "steigenberger alcazar":     9.2,
    "sunrise montemare":         9.2,
    "sunrise alora":             9.2,
    "baron palace sahl":         9.2,
    "serry beach":               9.2,
    "jaz makadi gardens":        9.2,
    "jaz makadi star":           9.3,
    "steigenberger pure life":   9.3,
    "rixos sharm adults":        9.3,
    "pickalbatros royal moderna":9.3,
    "pickalbatros royal grand":  9.3,
    "four seasons":              9.3,
    "coral sea imperial":        9.4,
    "jaz soma beach":            9.4,
    "titanic deluxe sharm":      9.4,
    "oberoi beach":              9.6,

    # добавлено из файла с рейтингами Booking (оценки ориентировочные, не перезаписывают таблицу выше)
    "amc royal":                 8.5,
    "aladdin beach":             8.4,
    "aurora oriental":           8.3,
    "iberotel palace":           9.1,
    "nubian island":             8.7,
    "nubian village":            8.6,
    "palm beach resort":         8.2,
    "parrotel beach resort":     8.4,
    "pharaoh azur":              8.3,
    "sharm cliff":               8.0,
    "sharming inn":              8.2,
    "sheraton sharm":            8.5,
    "sierra":                    8.8,
    "stella di mare beach":      9.3,
    "grand resort hurghada":     8.3,
    "turquoise beach":           8.1,
    "xperience sea breeze":      8.9,

    # добавлено вручную (Booking), по списку отелей без рейтинга
    "white hills sharm el sheikh - posh club":9.4,
    "white hills":                            9.2,
    "viva sharm":                             8.1,
    "coral hills":                            8.0,
    "jaz dahabeya":                           8.8,
    "eden rock":                              7.9,
    "magic life redsina":                     9.3,
    "xperience saint george":                 8.4,
    "happy life village":                     8.3,
    "retac qunay":                            8.2,
    "romance regency":                        8.9,
    "v hotel sharm":                          9.0,
    "megan halomy":                           7.6,
    "jaz elite palace":                       9.1,
    "parrotel lagoon":                        8.6,
    "amphoras beach":                         8.5,
    "dexon roma":                             7.5,
    "faraana heights":                        8.1,
    "sand beach":                             7.4,
    "el khan sharm":                          8.2,
    "invidia coral beach":                    8.3,
    "fiord club":                             8.0,
    "swiss inn resort":                       8.7,
    "ecotel dahab":                           8.1,
    "time coral nuweiba":                     8.0,
    "viking club":                            7.8,
    "sharm plaza":                            8.3,
    "strand beach":                           9.1,
    "bay view resort taba":                   8.4,
    "rosetta hotel":                          8.2,
    "dive inn resort":                        8.5,
    "dahab lagoon":                           8.6,
    "novotel palm":                           8.9,
    "sun & sea hotel hurghada":               7.5,
    "ivy cyrene":                             8.2,
    "marina sharm":                           8.6,
    "falcon hills":                           8.0,
    "falcon naama star":                      7.9,
    "lido sharm":                             8.8,
    "safir dahab":                            8.9,
    "mazar resort":                           7.9,
    "siva sharm":                             8.5,
    "ghazala garden":                         8.3,
    "sharm reef":                             8.2,
    "oriental rivoli":                        8.4,
    "sharm grand plaza":                      8.5,
    "faraana reef":                           8.4,
    "club reef":                              8.3,
    "cataract layalina":                      7.8,
    "tamra beach":                            8.5,
    "jaz fayrouz":                            8.9,
}


_TOP_INDEX = None


def _norm(s: str) -> str:
    import re
    return re.sub(r"[^a-z0-9 ]", "", s.lower().replace("é", "e").replace("ô", "o"))


def _top_rating(hotel_name: str):
    """Рейтинг из списка топ-отелей (top_hotels.py), если нет в таблице выше."""
    global _TOP_INDEX
    import re
    if _TOP_INDEX is None:
        try:
            from top_hotels import TOP_HOTELS
            _TOP_INDEX = {
                _norm(re.sub(r"\s*\(.*", "", n)): r
                for lst in TOP_HOTELS.values() for n, _s, r in lst
            }
        except Exception:
            _TOP_INDEX = {}
    n = _norm(re.sub(r"\s*\(.*", "", hotel_name))
    if n in _TOP_INDEX:
        return _TOP_INDEX[n]
    for k, v in _TOP_INDEX.items():
        if len(k) > 6 and (k in n or n in k):
            return v
    return None


def get_rating(hotel_name: str):
    """Возвращает (рейтинг, None) или (None, None)."""
    name = hotel_name.lower()
    for key, rating in HOTEL_RATINGS.items():
        if key in name:
            return rating, None
    top = _top_rating(hotel_name)
    if top:
        return top, None
    name_words = set(name.split())
    best_match = None
    best_count = 1
    for key, rating in HOTEL_RATINGS.items():
        key_words = set(key.split())
        common = len(key_words & name_words)
        if common > best_count:
            best_count = common
            best_match = (rating, None)
    return best_match if best_match else (None, None)
