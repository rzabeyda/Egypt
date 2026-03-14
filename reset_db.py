"""
python reset_db.py
Очищает историю отправленных туров — бот пришлёт все найденные туры заново.
"""
import sqlite3, os
DB = "data/tours.db"
if not os.path.exists(DB):
    print("БД не найдена — всё чисто")
else:
    conn = sqlite3.connect(DB)
    count = conn.execute("SELECT COUNT(*) FROM sent_tours").fetchone()[0]
    conn.execute("DELETE FROM sent_tours")
    conn.commit()
    conn.close()
    print(f"✅ Удалено {count} записей. Теперь запусти bot.py — туры придут заново.")
