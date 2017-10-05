
import sqlite3

conn = sqlite3.connect('reddit.db')

c = conn.cursor()
#conn.execute('drop table posts')
#conn.execute('drop table comment')

c = conn.cursor()
#c.execute('create table if not exists {0} (user_name text, password text)'.format('reddit_logins'))
#c.execute('insert into reddit_logins values(?,?)', ('dataphobes', 'SVUhgJCTZrPBeN2U'))

#c.execute('create table if not exists {0} (sub_name TEXT PRIMARY KEY)'.format('subreddit'))
#c.execute('insert into subreddit values(?)', ('aww',))
#c.execute('insert into subreddit values(?)', ('worldnews',))
#c.execute('insert into subredit values(?)', ('funny',))
conn.commit()
res = c.execute('select * from comment')
for i in res:
    print(i)



