import sqlite3

conn = sqlite3.connect('reddit.db', timeout=10)

c = conn.cursor()
#conn.execute('drop table posts')
#conn.execute('drop table comment')

c.execute('select * from reddit_logins')
for i in c:
    print(i)




