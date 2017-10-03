import sqlite3

conn = sqlite3.connect('reddit.db', timeout=10)

c = conn.cursor()
conn.execute('drop table posts')
conn.execute('drop table comment')

conn.commit()
c.execute('select * from comment')
for i in c:
    print(i)




