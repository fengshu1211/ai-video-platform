import sqlite3

DB = "/opt/ai-video-platform/backend/data.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()

# List tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("Tables:", tables)

# Clean
if "async_tasks" in tables:
    cur.execute("UPDATE async_tasks SET status='failed', progress_message='cancelled' WHERE status='pending' OR status='processing'")
    print(f"async_tasks updated: {cur.rowcount}")
else:
    print("async_tasks table NOT FOUND")

if "video_projects" in tables:
    cur.execute("UPDATE video_projects SET status='draft' WHERE status='processing'")
    print(f"video_projects updated: {cur.rowcount}")

conn.commit()
conn.close()
print("Done")
