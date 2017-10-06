
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
#conn.commit()
res = c.execute('select * from comment')
#res = c.execute("SELECT * FROM sqlite_master WHERE type='table';")
print(len(list(res)))
#for i in res:
#    print(i)

#a = [1,2,3]
#print(a[-10:0])



