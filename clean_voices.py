import sqlite3

conn = sqlite3.connect("/opt/ai-video-platform/backend/data.db")
cur = conn.cursor()

# Delete dialect voices
cur.execute("DELETE FROM voice_profiles WHERE voice_id LIKE '%shanxi%' OR voice_id LIKE '%liaoning%' OR voice_id LIKE '%Xiaobei%' OR voice_id LIKE '%Xiaoni%'")
print(f"Deleted dialects: {cur.rowcount}")

# Delete minimax duplicates (IDs 9-17)
cur.execute("DELETE FROM voice_profiles WHERE id > 8 AND provider='minimax' AND is_custom=0")
print(f"Deleted minimax dups: {cur.rowcount}")

# Show remaining
cur.execute("SELECT id, name, provider, voice_id FROM voice_profiles WHERE status='active' ORDER BY id")
for row in cur.fetchall():
    print(f"  #{row[0]} {row[1]} ({row[2]}) {row[3][:30]}")

conn.commit()
conn.close()
print("Done")
