
import sqlite3

conn = sqlite3.connect('reddit.db', timeout=10)

c = conn.cursor()
#conn.execute('drop table posts')
#conn.execute('drop table comment')

conn.execute('create table if not exists {0} (user_name text, password text)'.format('reddit_logins'))
conn.execute('insert into reddit_logins values(?,?)', ('dataphobes', 'SVUhgJCTZrPBeN2U'))
res = conn.execute('select * from reddit_logins')
for i in res:
    print(i)



