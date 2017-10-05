
from bs4 import BeautifulSoup
import traceback
import sqlite3
import time
import re
import datetime
import statistics
import operator
import random
import neural_network

subreddits = ['Askreddit', 'news','the_donald','politics', 'pics', 'worldnews', 'funny', 'videos','nfl', 'nba', 'todayilearned', 'dankmemes', 'aww', 'gifs', 'mma']

class post():
    def __init__(self, url, p_id):
        self.url = url
        self.p_id = p_id
        self.comments = []

class comment_data():
    def __init__(self, soup):
        self.soup = soup
        self.text = self.soup.find('div', {'class':'md'}).text
        self.time_str = self.soup.find('time')['datetime']
        self.comment_timestamp = datetime.datetime.strptime(self.time_str,'%Y-%m-%dT%H:%M:%S+00:00').timestamp()

        self.text2 = self.text.lower()
        self.text2 = self.text2.replace(r'\n','.')

        self.sentences = re.split('[.!?]+',self.text2)
        self.comment_words = []
        for i in self.sentences:
            self.comment_words.extend(re.split('[ .!?]+',i))

class reader():
    def __init__(self, session):
        self.name = ""
        self.reset_subreddit()
        self.put_sub_to_db()
        self.session = session
        #self.write_posts_and_comments_to_db()

        self.word_dict = {}
        self.sentence_count_dict = {}

    def read_all(self):
        temp = self.name
        for i in subreddits:
            print('reading posts in :', i)
            self.name = i
            self.get_post_list()
        self.name = temp
        self.write_posts_and_comments_to_db()

    def reset_subreddit(self):
        s_list = []
        conn = sqlite3.connect('reddit.db', timeout=10)
        res = conn.execute('select * from subreddit')
        for s in res:
            s_list.append(s[0])
        self.name= random.choice(s_list)
        conn.close()

    def put_sub_to_db(self):
        conn = sqlite3.connect('reddit.db')
        cursor = conn.cursor()
        cursor.execute('create table if not exists {0} (sub_name TEXT PRIMARY KEY)'.format('subreddit'))
        try:
            cursor.execute('insert into subreddit(sub_name) values(:sub_name)', {'sub_name': self.name})
        except:
            pass

        cursor.execute('create table if not exists {0} (subreddit TEXT, post_id TEXT UNIQUE, post_title TEXT, timestamp TEXT, data_permalink TEXT, comment_count int, upvotes int)'.format('posts'))
        cursor.execute('create table if not exists {0} (post_id TEXT, comment_id TEXT PRIMARY KEY, parent_id TEXT, timestamp TEXT, text TEXT, upvotes int)'.format('comment'))

        conn.commit()
        conn.close()

    def write_post(self, conn, p):
        #print(p.attrs)
        try:
            conn.execute('insert into posts values(?,?,?,?,?,?,?)', (self.name ,p['data-fullname'].split('_')[1], p.find('p',{'class':'title'}).find('a').text, p['data-timestamp'], p['data-permalink'], 0, 0) )
            print('Inserted post:', p['data-fullname'].split('_')[1], p.find('p',{'class':'title'}).find('a').text, p['data-timestamp'], p['data-permalink'], None, None)
            return (p['data-fullname'].split('_')[1], p.find('p',{'class':'title'}).find('a').text, p['data-timestamp'], p['data-permalink'], None, None)
        except:
            return (None, None, None, None, None, None)

    def get_post_list(self):
        conn = sqlite3.connect('reddit.db')
        tries = 3
        while tries >0:
            time.sleep(3)
            try:

                r = self.session.get('https://www.reddit.com/r/{0}/'.format(self.name))
                soup = BeautifulSoup(r.text, "html.parser")

                posts = soup.find('div', {'id':'siteTable'}).find_all('div', {'data-whitelist-status':'all_ads'}, recursive = False)

                print(len(posts))
                for p in posts:
                    self.write_post(conn, p)
                conn.commit()
                conn.close()
                print('writing posts done')
                conn.close()
                break
            except:
                traceback.print_exc()
                conn.close()
                tries -= 1
                #fix


    def write_comments(self, p, conn):
        try:
            r = self.session.get('https://www.reddit.com' + p[0])
            soup = BeautifulSoup(r.text, "html.parser")

            #print('https://www.reddit.com' + p[0])
            #print('comments',soup.find('a',{'data-event-action':'comments'}).text.replace(',','').split(' ')[0])
            #print('points',soup.find('span',{'class':'number'}).text.replace(',',''))

            comment_count = soup.find('a',{'data-event-action':'comments'}).text.replace(',','').split(' ')[0]
            upvotes = soup.find('span',{'class':'number'}).text.replace(',','')

            try:
                temp = int(comment_count) + int(upvotes)
            except:
                return

            conn.execute('update posts set upvotes = ? where post_id = ?', (upvotes, p[1],))
            conn.execute('update posts set comment_count = ? where post_id = ?', (comment_count, p[1],))

            comments = soup.find_all('div', {'class': re.compile("entry unvoted.*")})


            for c in comments:
                try:
                    time_str = c.find('time')['datetime']
                    comment_date = datetime.datetime.strptime(time_str,'%Y-%m-%dT%H:%M:%S+00:00')
                    comment_upvotes = c.find('span',{'class':'score unvoted'})['title']
                    comment_text = c.find('div', {'class':'md'}).text
                    comment_id = c.find('input', {'name':'thing_id'})['value']
                    try:
                        parent_id = c.find('a',{'data-event-action':'parent'})['href'].replace('#','')
                    except:
                        parent_id = None
                    try:
                        conn.execute('insert into comment values(?,?,?,?, ?,?)', (p[1].split('_')[0], comment_id.split('_')[1], parent_id,comment_date.timestamp(), comment_text,  comment_upvotes))
                        print('inserted comment:', (p[1].split('_')[0], comment_id.split('_')[1], parent_id,comment_date.timestamp(), comment_text,  comment_upvotes))
                        conn.commit()
                    except:
                        #add update
                        pass


                except:
                    pass
                    #traceback.print_exc()
        except:
            traceback.print_exc()

    def comment_similarity(self, c1, c2):
        c1_word = list(re.split(r'[^a-zA-Z0-9]+',c1.lower()))
        c2_words = list(re.split(r'[^a-zA-Z0-9]+', c2.lower()))

        value1 = 0
        for i in c1_word:
            if i in c2_words:
                c2_words.remove(i)

        return 1 - len(c2_words)/len(list(re.split(r'[^a-zA-Z0-9]+', c2.lower())))


    def write_posts_and_comments_to_db(self):
        conn = sqlite3.connect('reddit.db')

        res = conn.execute('select distinct data_permalink, post_id from posts')
        for p in res:
            #continue
            time.sleep(3)
            print(p)
            self.write_comments(p,conn)

        print('writing comments done')

        conn.commit()
        conn.close()

    def build_response_word_graph(self, sub):
        g = neural_network.response_word_graph()
        conn = sqlite3.connect('reddit.db')

        if sub is None:
            res = conn.execute('select distinct a.comment_id, a.parent_id, a.post_id, a.text, a.upvotes, b.text, a.timestamp from comment a join comment b on a.parent_id = b.comment_id order by a.timestamp')
        else:
            #TODO: add subreddit specific learning
            res = conn.execute('select distinct a.comment_id, a.parent_id, a.post_id, a.text, a.upvotes, b.text from comment a join comment b on a.parent_id = b.comment_id')

        result_list = res.fetchall()
        print('num of results:', len(result_list))
        for r in result_list:
            child_words = re.split(r'[^a-zA-Z0-9]+',r[3].lower())
            parent_words = re.split(r'[^a-zA-Z0-9]+',r[5].lower())
            for i in child_words:
                for j in parent_words:
                    try:
                        g.add_item(j, i, int(r[4]))
                    except:
                        traceback.print_exc()
        conn.close()
        return g

    def strategy1(self):
        comment_min_len = 10
        min_comments = 2
        similarity_threshold = .9
        results = []
        print("Starting learning words")
        g = self.build_response_word_graph(None)
        print('Finished learning.')

        #pick post, new post with high upvotes
        conn = sqlite3.connect('reddit.db')
        r = self.session.get('https://www.reddit.com/r/{0}/top/?sort=top&t=hour'.format(self.name))
        soup = BeautifulSoup(r.text,'html.parser')
        ps = soup.find('div', {'id':'siteTable'}).find_all('div', {'data-whitelist-status':'all_ads'}, recursive = False)

        p_url = None
        p_id = None

        return_value= None
        posts = []
        for p in ps:
            post_data = self.write_post(conn, p)
            p_url = post_data[3]
            p_id = post_data[0]
            temp_post = post(p_url, p_id)

            print('p_id, P_url:', p_id, p_url)
            if p_url is None or p_id is None:
                continue

            #pick comment, second earliest since earliest is often mod post
            r = self.session.get('https://www.reddit.com' + p_url)
            soup = BeautifulSoup(r.text,'html.parser')
            comment_table = soup.find('div', {'class':'sitetable nestedlisting'})
            comments = comment_table.find_all('div', {'class': re.compile("entry unvoted.*")})
            if len(comments) < min_comments:
                return_value = 'Not enough comments'
                continue
            else:
                return_value = None

            #sort by timestamp
            comments_clean = []

            for c in comments:
                try:
                    if len(c.find('div', {'class':'md'}).text.lower()) < comment_min_len or 'http' in c.find('div', {'class':'md'}).text.lower():
                        continue
                    else:
                        comments_clean.append(comment_data(c))
                except:
                    pass
            comments_clean.sort(key = operator.attrgetter('comment_timestamp'), reverse = True)
            temp_post.comments=comments_clean
            posts.append(temp_post)

        replied = False
        for p in posts:
            #run dict maker only accepting sentences that share words with title and/or post
            for c in p.comments:
                self.sentence_dict = {}
                if p.url is None or p.p_id is None:
                    continue

                res = conn.execute('select distinct comment.comment_id, comment.post_id, comment.text, comment.upvotes, posts.data_permalink from posts join comment on posts.post_id = comment.post_id where subreddit = ?', (self.name,))

                sorting_structure = []
                for r in res:
                    text_post = r[2]
                    text_post = text_post.lower()
                    normalized_sentence = text_post.lower().strip()
                    if len(normalized_sentence) < comment_min_len:
                        continue

                    implied_score = g.values_statement(c.text, r[2])

                    if 'http' not in text_post and self.comment_similarity(text_post, c.text)<similarity_threshold:
                        sorting_structure.append((r[0], r[4], implied_score, text_post))

                sorting_structure.sort(key=operator.itemgetter(2), reverse=True)
                current_comment = sorting_structure[0]

                try:
                    print('score: ', sorting_structure[0][1])
                    print('p_id:',p_id)
                    print('parent comment:', c.text)
                    print('intended comment:', current_comment[3])
                    print('returning:', ('https://www.reddit.com'+current_comment[1] + current_comment[0], current_comment[3], current_comment[2]))
                    #put optimal number of sentences and post it as response
                    results.append(('https://www.reddit.com'+current_comment[1] + current_comment[0], current_comment[3], current_comment[2]))#full url, text, expected value
                except:
                    traceback.print_exc()
        results.sort(key=operator.itemgetter(2), reverse=True)
        return results

    def pick_strategy_and_sub(self, num):
        results = self.strategy1()

        for i in results:
            print(i)
        return results[0:num]

