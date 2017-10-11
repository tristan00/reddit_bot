import sqlite3
import sys

conn = sqlite3.connect('reddit.db')
c = conn.cursor()



#conn.execute('drop table posts')
#conn.execute('drop table comment')
#c.execute('create table if not exists {0} (user_name text, password text)'.format('reddit_logins'))
#c.execute('insert into reddit_logins values(?,?)', ('dataphobes', 'SVUhgJCTZrPBeN2U'))
#c.execute('create table if not exists {0} (sub_name TEXT PRIMARY KEY)'.format('subreddit'))
#c.execute('insert into subreddit values(?)', ('aww',))
#c.execute('insert into subreddit values(?)', ('worldnews',))
#c.execute('insert into subredit values(?)', ('funny',))
#conn.commit()

subreddits = ['Askreddit', 'news','politics', 'pics', 'worldnews', 'funny', 'videos','nfl', 'nba', 'todayilearned', 'me_irl', 'aww', 'gifs', 'mma', 'trees']
for s in subreddits:
    c.execute('delete from comment')
conn.commit()

res = c.execute('select distinct subreddit from posts')
print(list(res))
#conn.close()

#res = c.execute('delete from comment')
#conn.commit()
#res = c.execute("SELECT * FROM sqlite_master WHERE type='table';")
#for i in res:
#print(i)
#sys.getsizeof(object)

#a = [1,2,3]
#print(a[-10:0])
