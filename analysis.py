
from bs4 import BeautifulSoup
import traceback
import sqlite3
import time
import re
import datetime
import statistics
import operator
import random
import math

subreddits = ['Askreddit', 'news','the_donald','politics', 'pics', 'worldnews', 'funny', 'videos','nfl', 'nba', 'todayilearned', 'dankmemes', 'me_irl', 'aww', 'gifs', 'mma']
random.shuffle(subreddits)


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
        self.put_sub_to_db()
        self.session = session
        #self.write_posts_and_comments_to_db()

        self.word_dict = {}
        self.sentence_count_dict = {}

    def read_all(self):

        for i in subreddits:
            print('reading posts in :', i)
            subreddit = i
            self.get_post_list(subreddit)
        self.write_posts_and_comments_to_db()

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

    def get_post_list(self, subreddit):
        conn = sqlite3.connect('reddit.db')
        tries = 3
        while tries >0:
            time.sleep(3)
            try:

                r = self.session.get('https://www.reddit.com/r/{0}/'.format(subreddit))
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
                        conn.execute('update comment set upvotes = ? where comment_id = ?', (upvotes, comment_id.split('_')[1],))
                        print('updated comment:', (p[1].split('_')[0], comment_id.split('_')[1], parent_id,comment_date.timestamp(), comment_text,  comment_upvotes))
                        conn.commit()
                        pass
                except:
                    pass
                    #TODO: make sure the error is always the comment_upvote part
                    #traceback.print_exc()
        except:
            traceback.print_exc()

    def write_posts_and_comments_to_db(self):
        conn = sqlite3.connect('reddit.db')

        res = conn.execute('select distinct data_permalink, post_id from posts order by timestamp desc')
        for p in res:
            #continue
            time.sleep(3)
            print(p)
            self.write_comments(p,conn)

        print('writing comments done')

        conn.commit()
        conn.close()

    def build_response_graph(self, graph_type):
        #graph types:
        #1: analyzes comment response words
        #2: analyzes title words

        g = response_word_graph()
        conn = sqlite3.connect('reddit.db')
        res = conn.execute('select distinct a.comment_id, a.parent_id, a.post_id, a.text, a.upvotes, b.text, a.timestamp, a.post_id from comment a join comment b on a.parent_id = b.comment_id order by a.timestamp')

        for r in res:
            #print(r)

            if (graph_type == 1):
                child_words = split_comments(r[3])
                parent_words = split_comments(r[5])
            if (graph_type == 2):
                child_words = split_comments(r[3])
                parent_words = split_comments(r[7])

            for i in child_words:
                for j in parent_words:
                    try:
                        g.add_item(j, i, int(r[4]))
                    except:
                        traceback.print_exc()

        conn.close()
        return g

    def strategy1(self, subreddit, max_results):
        comment_min_len = 10
        min_comments = 2
        similarity_threshold = .9
        results = []
        print("Starting learning words")
        g_comments = self.build_response_graph(1)
        g_title = self.build_response_graph(2)
        print('Finished learning.')

        #pick post, new post with high upvotes
        conn = sqlite3.connect('reddit.db')
        r = self.session.get('https://www.reddit.com/r/{0}/top/?sort=top&t=hour'.format(subreddit))
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

        possible_comment_list = list(conn.execute('select distinct comment.comment_id, comment.post_id, comment.text, comment.upvotes, posts.data_permalink, posts.data_permalink, posts.post_title from posts join comment on posts.post_id = comment.post_id where posts.subreddit like ?', (subreddit,)).fetchall())

        for p in posts:
            #run dict maker only accepting sentences that share words with title and/or post
            for c in p.comments:
                self.sentence_dict = {}

                comment_id = c.soup.find('input', {'name':'thing_id'})['value'].split('_')[1]
                comment_permalink = None

                if p.url is None or p.p_id is None:
                    continue

                sorting_structure = []
                for r in possible_comment_list:
                    implied_reply_score = g_comments.values_statement(split_comments(c.text), split_comments(r[2]))
                    implied_title_score = g_title.values_statement(split_comments(c.text),split_comments(r[6]))

                    if 'http' not in r[2]:
                        sorting_structure.append((r[0], r[4], math.sqrt((implied_reply_score*implied_reply_score) + (implied_title_score*implied_title_score)), r[2]))

                sorting_structure.sort(key=operator.itemgetter(2), reverse=True)
                current_comment = sorting_structure[0]

                try:
                    print('returning:', ('https://www.reddit.com'+ p.url + comment_id, current_comment[3], current_comment[2]))
                    #put optimal number of sentences and post it as response
                    results.append(('https://www.reddit.com'+ p.url + comment_id, current_comment[3], current_comment[2]))#full url, text, expected value
                except:
                    traceback.print_exc()
                if len(results) >=max_results:
                    results.sort(key=operator.itemgetter(2), reverse=True)
                    return results
        results.sort(key=operator.itemgetter(2), reverse=True)
        return results

    def run_strategy(self, num, subreddit, strat):
        results = self.strategy1(subreddit, 5)

        for i in results:
            print(i)
        return results[0:num]

class response_word_graph():
    def __init__(self):
        self.parent_nodes = {}
        self.child_nodes = {}

    def add_item(self, parent_word, child_word, value):
        self.child_nodes.setdefault(child_word, node(child_word)).add_value(parent_word, value)

    def values_statement(self, parent_words, child_words):

        child_words_value = []
        for w in child_words:
            temp_value = []
            for w2 in parent_words:
                try:
                    temp_value.append(self.child_nodes[w].get_edge_median(w2))
                except:
                    #key error
                    temp_value.append(0)
            child_words_value.append(statistics.mean(temp_value))

        return sum(child_words_value)/max(len(child_words),len(parent_words))

class node():
    def __init__(self, content):
        self.min_length = 5
        self.max_length = 100
        self.content = content.lower()
        self.edges = {}
        self.average = 0
        self.median = 0

    def add_value(self, edge, value):
        self.edges.setdefault(edge, []).append(value)
        if len(self.edges[edge]) > self.max_length:
            self.edges[edge] = self.edges[edge][-(self.max_length):]

    def get_edge_value(self, in_word):
        if in_word in self.edges.keys():
            return self.edges[in_word]
        return 0

    def get_edge_median(self, in_word):
        if in_word in self.edges.keys() and len(self.edges[in_word])>=self.min_length:
            return statistics.median(self.edges[in_word])
        return 0

    def get_edge_mean(self, in_word):
        if in_word in self.edges.keys() and len(self.edges[in_word])>=self.min_length:
            return statistics.mean(self.edges[in_word])
        return 0

def comment_similarity(c1, c2):
    c1_word = list(re.split(r'[^a-zA-Z0-9]+',c1.lower()))
    c2_words = list(re.split(r'[^a-zA-Z0-9]+', c2.lower()))

    value1 = 0
    for i in c1_word:
        if i in c2_words:
            c2_words.remove(i)

    return 1 - len(c2_words)/len(list(re.split(r'[^a-zA-Z0-9]+', c2.lower())))

def split_comments(c1):
    c1_word = list(set(list(re.split(r"[^a-zA-Z0-9']+", c1.lower()))))

    res = []
    value1 = 0
    for i in c1_word:
        if len(i)>2:
            res.append(i)

    return res