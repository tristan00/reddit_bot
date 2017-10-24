import sqlite3
import sys
import datetime
import time

conn = sqlite3.connect('reddit.db')
c = conn.cursor()

#c.execute('drop table sentiment_movie_data')
#c.execute('create table if not exists model_word_mapping (model text unique, word text, rank int, marker int)')
#conn.commit()


#conn.execute('drop table posts')
#conn.execute('drop table comment')
#c.execute('create table if not exists {0} (user_name text, password text)'.format('reddit_logins'))
#c.execute('create table if not exists {0} (sub_name TEXT PRIMARY KEY)'.format('subreddit'))
#c.execute('insert into subreddit values(?)', ('aww',))
#c.execute('insert into subreddit values(?)', ('worldnews',))
#c.execute('insert into subredit values(?)', ('funny',))
#conn.commit()

#subreddits = ['Askreddit', 'news','politics', 'pics', 'worldnews', 'funny', 'videos','nfl', 'nba', 'todayilearned', 'me_irl', 'aww', 'gifs', 'mma', 'trees']
#conn.commit()

#res = c.execute('select distinct subreddit from posts')
#print(list(res))
#conn.close()

#res = c.execute('delete from comment')
#conn.commit()

#conn.commit()
res = c.execute("SELECT * FROM sqlite_master WHERE type='table';")
inputs = list(conn.execute('select c1.text, c1.upvotes, c2.text, c2.upvotes, p.subreddit, p.post_title, p.timestamp, c1.timestamp, c2.timestamp '
                           'from comment c1 join comment c2 on c1.comment_id = c2.parent_id  join posts p on c1.post_id = p.post_id '
                           'where c1.upvotes is not null and c2.upvotes is not null').fetchall())
#res = c.execute("SELECT * FROM comment;")
#res =conn.execute('select distinct comment.comment_id, comment.post_id, comment.text, comment.upvotes, posts.data_permalink, posts.data_permalink, posts.post_title from posts join comment on posts.post_id = comment.post_id where posts.subreddit like ?', ('dankmemes',)).fetchall()

#res = c.execute("update posts set subreddit = ? where data_permalink like ?", ('totallynotrobots', '%totallynotrobots%',))
#conn.commit()
#c.execute('drop table log')
#res = c.execute("CREATE TABLE log (url TEXT, parent_url text primary key, subreddit text, strat int, result int, comment text, timestamp int)")
#conn.commit()

#subreddit = ''
#res = conn.execute("select distinct comment.comment_id, comment.post_id, comment.text, comment.upvotes, posts.data_permalink, posts.data_permalink, posts.post_title from posts join comment on posts.post_id = comment.post_id").fetchall()
#res = conn.execute('select * from log order by result').fetchall()
#res = list(conn.execute('select subreddit, strat, count(result), avg(result) from log where result is not null group by subreddit, strat').fetchall())
#res = conn.execute('delete from log where result is null').fetchall()
#conn.commit()

#res = conn.execute('select * from comment').fetchall()
#subreddit = 'dankmemes'
#res = conn.execute('select distinct a.comment_id, a.parent_id, a.post_id, a.text, a.upvotes, b.text, a.timestamp, a.post_id from comment a join comment b on a.parent_id = b.comment_id join posts c on a.post_id like c.post_id where c.subreddit like ? order by a.timestamp', (subreddit,))

for i in res:
    print(i)


#sys.getsizeof(object)

#a = [1,2,3]
#print(a[-10:0])
