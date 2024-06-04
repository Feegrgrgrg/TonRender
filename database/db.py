import sqlite3



conn = sqlite3.connect('users.db')
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users
             (id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, last_name TEXT, free_draws INTEGER DEFAULT 1)''')

conn.commit()



async def add_user_to_db(user):
    c.execute("SELECT * FROM users WHERE id=?", (user.id,))
    existing_user = c.fetchone()
    if existing_user:
        print("User already exists in the database.")
        return
    c.execute("INSERT INTO users (id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
              (user.id, user.username, user.first_name, user.last_name))
    conn.commit()
    
    
