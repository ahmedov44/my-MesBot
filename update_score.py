import sqlite3

conn = sqlite3.connect('bot.db')
cursor = conn.cursor()

user_id = 5257767076
new_score = 1500

cursor.execute("UPDATE scores SET score = ? WHERE user_id = ?", (new_score, user_id))
conn.commit()

conn.close()

print("Score updated!")
