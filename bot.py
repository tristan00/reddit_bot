
import requests
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import os
from bs4 import BeautifulSoup
import traceback
import sqlite3
import time
import re
import datetime
import numpy as np
import statistics
import operator
import random
import math
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
import multiprocessing

reddit_sleep_time = 3
writing_sleep_time= 600
discount_rate = .8
num_of_strats = 3
commented_list = []
commented_parent_list = []
user_name = None
db_lock = multiprocessing.Lock()

main_bot = None
main_reader = None
sql_file = 'reddit_db.sqlite'
os.chdir(os.path.dirname(os.path.realpath(__file__)))
subreddits = ['dankmemes', 'me_irl', 'surrealmemes', 'totallynotrobots', 'dota2', 'memes', 'youdontsurf', 'wholesomememes', 'comedycemetery', 'jokes', 'cringepics', 'insanepeoplefacebook', 'politics']
read_only_subs = []
random.shuffle(subreddits)

class post():
    def __init__(self, url, p_id):
        self.url = url
        self.p_id = p_id
        self.comments = []

class comment_data():
    def __init__(self, soup, p_id):
        self.soup = soup
        self.p_id = p_id
        self.parent_url = None

    def read_timestamp(self):
        self.time_str = self.soup.find('time')['datetime']
        self.comment_timestamp = datetime.datetime.strptime(self.time_str,'%Y-%m-%dT%H:%M:%S+00:00').timestamp()

    def read_text(self):
        self.text = self.soup.find('div', {'class':'md'}).text
        self.comment_words = split_comments_into_words(self.text)

    def read_upvotes(self):
        self.comment_upvotes = self.soup.find('span',{'class':'score unvoted'})['title']

    def read_all_parameters(self):
        self.read_timestamp()
        self.read_text()
        self.comment_id = self.soup.find('input', {'name':'thing_id'})['value']
        self.comment_upvotes = self.soup.find('span',{'class':'score unvoted'})['title']
        try:
            self.parent_id = self.soup.find('a',{'data-event-action':'parent'})['href'].replace('#','')
        except:
            self.parent_id = None

    def toDB(self, cursur):
        try:
            cursur.execute('insert into comment values(?,?,?,?, ?,?)', (self.p_id.split('_')[0], self.comment_id.split('_')[1], self.parent_id, self.comment_timestamp, self.text,  self.comment_upvotes))
            print('inserted comment:', (self.p_id.split('_')[0], self.comment_id.split('_')[1], self.parent_id, self.comment_timestamp, self.text,  self.comment_upvotes))
        except:
            try:
                cursur.execute('update comment set upvotes = ? where comment_id = ?', (self.comment_upvotes, self.comment_id.split('_')[1],))
                print('updated comment:', (self.p_id.split('_')[0], self.comment_id.split('_')[1], self.parent_id, self.comment_timestamp, self.text,  self.comment_upvotes))
            except:
                traceback.print_exc()

class Reader():
    def __init__(self, session, conn):
        self.name = ""
        self.put_sub_to_db(conn)
        self.session = session
        #self.write_posts_and_comments_to_db()

        self.word_dict = {}
        self.sentence_count_dict = {}
        self.g_comments = {}
        self.g_title = {}
        self.g_words = {}
        self.g_sentences = {}

        self.possible_comments = {}
        self.get_log(conn)

    def is_comment_valid(self, comment_text, p):
        #TODO: comment/fix this method
        if 'http' not in comment_text and comment_text not in commented_list and 'AutoBotDetection' not in comment_text:
            for i in p.comments:
                if comment_text in i.text:
                    return False
            return True

    def get_log(self, conn):
        global commented_list
        global commented_parent_list

        conn.execute('create table if not exists log (url TEXT, parent_url text primary key, subreddit text, strat int, result int, comment text)')
        res = list(conn.execute('select distinct comment, parent_url from log').fetchall())
        for i in res:
            commented_list.append(i[0])
            if (i[1] is not None):
                commented_parent_list.append(i[1])
        conn.commit()


    def read_all(self, count):
        for i in (subreddits + read_only_subs):
            print('reading posts in :', i)
            self.get_post_list(i)
        self.write_comments_to_db(int(count/2), 1)
        self.write_comments_to_db(int(count/2), 0)


    def update_log(self):
        db_lock.acquire()
        conn = sqlite3.connect('reddit.db')

        #check profile for latest posts
        r = self.session.get('https://www.reddit.com/user/{0}/'.format(user_name))
        soup = BeautifulSoup(r.text, "html5lib")
        for c in soup.find_all('div', {'data-type':'comment'}):
            try:
                text = c.find('div',{'class':'md'}).text
                value = int(c.find('span',{'class':'score unvoted'})['title'])
                perma_url = 'https://www.reddit.com' + c.find('a',{'data-event-action':'permalink'})['data-href-url']
                conn.execute('update log set url = ?, result = ? where comment = ?', (perma_url, value, text,))
                conn.commit()
            except:
                traceback.print_exc()
        db_lock.release()

        #go get all recorded posts
        results = list(conn.execute('select url from log where url is not null').fetchall())
        for result in results:
            try:
                r = self.session.get(result[0])
                soup = BeautifulSoup(r.text, "html5lib")
                value = soup.find('div', {'data-type':'comment'}).find('span', {'class':'score unvoted'})['title']
                conn.execute('update log set  result = ? where url = ?', (value, result[0],))
                conn.commit()
            except:
                traceback.print_exc()
        conn.close()

    def put_sub_to_db(self, conn):

        #TODO: create initial db creation code
        conn.execute('create table if not exists {0} (sub_name TEXT PRIMARY KEY)'.format('subreddit'))
        conn.execute('create table if not exists {0} (subreddit TEXT, post_id TEXT UNIQUE, post_title TEXT, timestamp TEXT, data_permalink TEXT, comment_count int, upvotes int)'.format('posts'))
        conn.execute('create table if not exists {0} (post_id TEXT, comment_id TEXT PRIMARY KEY, parent_id TEXT, timestamp TEXT, text TEXT, upvotes int)'.format('comment'))


    def write_post(self, conn, p, subreddit):
        #print(p.attrs)
        try:
            print('Inserting post:', p['data-fullname'].split('_')[1], p.find('p',{'class':'title'}).find('a').text, p['data-timestamp'], p['data-permalink'], None, None)
            try:
                conn.execute('insert into posts values(?,?,?,?,?,?,?)', (subreddit ,p['data-fullname'].split('_')[1], p.find('p',{'class':'title'}).find('a').text, p['data-timestamp'], p['data-permalink'], 0, 0) )
            except:
                pass
            return (p['data-fullname'].split('_')[1], p.find('p',{'class':'title'}).find('a').text, p['data-timestamp'], p['data-permalink'], None, None)
        except:
            traceback.print_exc()
            return (None, None, None, None, None, None)

    def get_post_list(self, subreddit):
        db_lock.acquire()
        conn = sqlite3.connect('reddit.db')
        time.sleep(reddit_sleep_time)
        try:
            r = self.session.get('https://www.reddit.com/r/{0}/'.format(subreddit))
            soup = BeautifulSoup(r.text, "html.parser")

            posts = soup.find('div', {'id':'siteTable'}).find_all('div', {'data-whitelist-status':'all_ads'}, recursive = False)

            print(len(posts))
            for p in posts:
                self.write_post(conn, p, subreddit)
            conn.commit()
            conn.close()
            print('writing posts done')
            conn.close()
            db_lock.release()
        except:
            traceback.print_exc()
            conn.close()
            db_lock.release()

    def update_posts(self, soup, conn, p_id):
        comment_count = soup.find('a',{'data-event-action':'comments'}).text.replace(',','').split(' ')[0]
        upvotes = soup.find('span',{'class':'number'}).text.replace(',','')
        conn.execute('update posts set upvotes = ? where post_id = ?', (upvotes, p_id,))
        conn.execute('update posts set comment_count = ? where post_id = ?', (comment_count, p_id,))
        return soup.find_all('div', {'class': re.compile("entry unvoted.*")})

    def write_comments(self, p_url, p_id, conn):
        r = self.session.get('https://www.reddit.com' + p_url)
        soup = BeautifulSoup(r.text, "html.parser")
        try:
            self.update_posts(soup, conn, p_id)
        except:
            traceback.print_exc()
            return
        comment_soup = soup.find_all('div', {'class': re.compile("entry unvoted.*")})
        comment_list = []
        cursor = conn.cursor()
        for c in comment_soup:
            try:
                temp_c = comment_data(c, p_id)
                temp_c.read_all_parameters()
                temp_c.toDB(cursor)
            except:
                pass
                #traceback.print_exc()
        conn.commit()

    def write_comments_to_db(self, count, shuffle):
        db_lock.acquire()
        conn = sqlite3.connect('reddit.db')
        res = list(conn.execute('select distinct data_permalink, post_id from posts order by timestamp desc').fetchall())
        if shuffle == 1:
            random.shuffle(res)
        #res = conn.execute('select distinct data_permalink, post_id from posts')
        if count is None:
            count = len(res)
        for p in res[0:count]:
            time.sleep(reddit_sleep_time)
            print(p)
            try:
                self.write_comments(p[0], p[1],conn)
            except:
                traceback.print_exc()

        print('writing comments done')
        conn.commit()
        conn.close()
        db_lock.release()

    def build_response_graph(self, graph_type, subreddit):
        #graph types:
        #1: analyzes comment response words
        #2: analyzes title words

        if (graph_type == 1):
            g = response_word_graph(5)
        elif (graph_type == 2):
            g = response_word_graph(3)
        elif (graph_type == 3):
            g = response_word_graph(3)
        else:
            g = response_word_graph(3)

        db_lock.acquire()
        conn = sqlite3.connect('reddit.db')
        res_list = list(conn.execute('select distinct a.comment_id, a.parent_id, a.post_id, a.text, a.upvotes, b.text, a.timestamp, a.post_id from comment a join comment b on a.parent_id = b.comment_id join posts c on a.post_id like c.post_id where c.subreddit like ? order by a.timestamp', (subreddit,)).fetchall())

        value_list = []
        for i in res_list:
            value_list.append(int(i[4]))

        for r in res_list:
            if (graph_type == 1):
                child_words = split_comments_into_words(r[3])
                parent_words = split_comments_into_words(r[5])
            if (graph_type == 2):
                child_words = split_comments_into_words(r[3])
                parent_words = split_comments_into_words(r[7])
            if (graph_type == 3):
                child_words = [r[3]]
                parent_words = [r[5]]
            if (graph_type == 4):
                child_words = split_comments_into_sentences(r[3])
                parent_words = split_comments_into_sentences(r[5])

            for i in child_words:
                for j in parent_words:
                    try:
                        g.add_item(j, i, get_percentile(value_list, int(r[4])))
                    except:
                        traceback.print_exc()
        conn.close()
        db_lock.release()
        g.calculate_all_means()
        return g

    def build_graphs(self, sub):
        print('building graphs')
        self.g_words[sub] = self.build_response_graph(1, sub)
        self.g_title[sub] = self.build_response_graph(2, sub)
        self.g_comments[sub] = self.build_response_graph(3, sub)
        self.g_sentences[sub] = self.build_response_graph(4, sub)

    def dereference_graphs(self, sub):
        print('building graphs')
        self.g_words.pop(sub,None)
        self.g_title.pop(sub,None)
        self.g_comments.pop(sub,None)
        self.g_sentences.pop(sub,None)

    def get_new_posts_ready_to_analyze(self, conn, subreddit, sorting):
        comment_min_len = 5
        min_comments = 2
        if sorting == 0:
            r = self.session.get('https://www.reddit.com/r/{0}/top/?sort=top&t=hour'.format(subreddit))
        elif sorting == 1:
            r = self.session.get('https://www.reddit.com/r/{0}/new/'.format(subreddit))
        elif sorting == 2:
            r = self.session.get('https://www.reddit.com/r/{0}/'.format(subreddit))
        soup = BeautifulSoup(r.text,'html.parser')
        ps = soup.find('div', {'id':'siteTable'}).find_all('div', {'data-whitelist-status':'all_ads'}, recursive = False)

        posts = []
        for p in ps:
            post_data = self.write_post(conn, p, subreddit)
            p_url = post_data[3]
            p_id = post_data[0]
            temp_post = post(p_url, p_id)

            print(' p_id, P_url:', p_id, p_url)
            if p_url is None or p_id is None:
                continue

            #pick comment, second earliest since earliest is often mod post
            r = self.session.get('https://www.reddit.com' + p_url)
            soup = BeautifulSoup(r.text,'html.parser')
            comment_table = soup.find('div', {'class':'sitetable nestedlisting'})
            comments = comment_table.find_all('div', {'class': re.compile("entry unvoted.*")})
            if len(comments) < min_comments:
                continue

            comments_clean = []
            for c in comments:
                try:
                    if len(c.find('div', {'class':'md'}).text.lower()) < comment_min_len or 'http' in c.find('div', {'class':'md'}).text.lower():
                        continue
                    else:
                        try:
                            temp_c = comment_data(c, p_id)
                            temp_c.read_timestamp()
                            temp_c.read_text()
                            comments_clean.append(temp_c)
                        except:
                            traceback.print_exc()
                except:
                    pass
            comments_clean.sort(key = operator.attrgetter('comment_timestamp'), reverse = True)
            temp_post.comments=comments_clean
            posts.append(temp_post)
        return posts

    def get_possible_comment_list(self, subreddit, conn):
        self.possible_comments.setdefault(subreddit,[])
        if len(self.possible_comments[subreddit]) == 0:
            for i in conn.execute('select distinct comment.comment_id, comment.post_id, comment.text, comment.upvotes, posts.data_permalink, posts.data_permalink, posts.post_title from posts join comment on posts.post_id = comment.post_id where posts.subreddit like ?', (subreddit,)).fetchall():
                self.possible_comments[subreddit].append(i)
        return self.possible_comments[subreddit]

    def execute_strategy(self, subreddit, max_results, post_sorting, strat):
        results = []
        db_lock.acquire()
        conn = sqlite3.connect('reddit.db')
        posts = self.get_new_posts_ready_to_analyze(conn, subreddit, post_sorting)
        possible_comment_list = self.get_possible_comment_list(subreddit, conn)
        conn.close()
        db_lock.release()

        for p in posts:
            for c in p.comments:
                try:
                    if 'deleted' in  c.soup.find('input', {'name':'thing_id'})['value']:
                        continue
                    comment_id = c.soup.find('input', {'name':'thing_id'})['value'].split('_')[1]
                except:
                    #TODO: add check for deleted comment
                    traceback.print_exc()
                    continue
                if p.url is None or p.p_id is None:
                    continue
                sorting_structure = []
                for r in possible_comment_list:
                    score = 0
                    if strat == 1:
                        implied_reply_score = self.g_words[subreddit].values_statement_by_mean(split_comments_into_words(c.text), split_comments_into_words(r[2]))
                        implied_title_score = self.g_title[subreddit].values_statement_by_mean(split_comments_into_words(c.text),split_comments_into_words(r[6]))
                        implied_sentence_score = self.g_sentences[subreddit].values_statement_by_mean(split_comments_into_sentences(c.text),split_comments_into_sentences(r[2]))
                        score = math.pow((implied_reply_score*implied_reply_score) + (implied_title_score*implied_title_score) + (implied_sentence_score*implied_sentence_score), 1/3)

                    elif strat == 2:
                        implied_reply_score = self.g_comments[subreddit].values_statement_by_mean([c.text], [r[2]])
                        score = implied_reply_score

                    elif strat == 3:
                        implied_sentence_score = self.g_sentences[subreddit].values_statement_by_mean(split_comments_into_sentences(c.text),split_comments_into_sentences(r[2]))
                        score = implied_sentence_score

                    if self.is_comment_valid(r[2], p):
                        sorting_structure.append((r[0], r[4], score, r[2]))

                if len(sorting_structure) == 0:
                    continue
                sorting_structure.sort(key=operator.itemgetter(2), reverse=True)
                current_comment = sorting_structure[0]

                try:
                    if current_comment[2] > 0.5:
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
        global commented_list
        results = []
        try:
            results.extend(self.execute_strategy(subreddit, 5*num, 0, strat))
            if len(results) == 0:
                print('first filter failed, attempting wider scope')
                time.sleep(reddit_sleep_time)
                results.extend(self.execute_strategy(subreddit, 5*num, 1, strat))

            if len(results) == 0:
                print('second filter failed, attempting wider scope')
                time.sleep(reddit_sleep_time)
                results.extend(self.execute_strategy(subreddit, 5*num, 2, strat))
            print('Results:')
            for i in results:
                print(i)
        except:
            traceback.print_exc()
        commented_list.extend(results[0:num])
        return results[0:num]

class response_word_graph():
    def __init__(self, min_results_per_node):
        self.parent_nodes = {}
        self.child_nodes = {}
        self.min_results_per_node = min_results_per_node

    def add_item(self, parent_word, child_word, value):
        self.child_nodes.setdefault(child_word, node(child_word, self.min_results_per_node)).add_value(parent_word, value)

    def values_statement_by_median(self, parent_words, child_words):
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

    def values_statement_by_mean(self, parent_words, child_words):
        child_words_value = []
        for w in child_words:
            temp_value = []
            for w2 in parent_words:
                try:
                    temp_value.append(self.child_nodes[w].get_edge_mean(w2))
                except:
                    #key error
                    temp_value.append(0)
            child_words_value.append(statistics.mean(temp_value))

        return sum(child_words_value)/max(len(child_words),len(parent_words))

    def calculate_all_means(self):
        for i in self.child_nodes.keys():
            self.child_nodes[i].calculate_all_means()

class node():
    def __init__(self, content, min_results_per_node):
        self.min_length = min_results_per_node
        self.max_length = 1000
        self.content = content.lower()
        self.edges = {}
        self.mean = {}
        self.median = {}

    def add_value(self, edge, value):
        self.edges.setdefault(edge, []).append(value)
        if len(self.edges[edge]) > self.max_length:
            self.edges[edge] = self.edges[edge][-(self.max_length):]

    def get_edge_value(self, in_word):
        if in_word in self.edges.keys():
            return self.edges[in_word]
        return 0

    def get_edge_median(self, in_word):
        median = self.median.get(in_word, None)
        if median is not None:
            return median
        elif in_word in self.edges.keys() and len(self.edges[in_word])>=self.min_length:
            self.median[in_word] = statistics.median(self.edges[in_word])
            return self.median[in_word]
        return 0

    def get_edge_mean(self, in_word):
        mean = self.mean.get(in_word, None)
        if mean is not None:
            return mean
        elif in_word in self.edges.keys() and len(self.edges[in_word])>=self.min_length:
            self.mean[in_word] = statistics.mean(self.edges[in_word])
            return self.mean[in_word]
        return 0

    def calculate_all_means(self):
        for i in self.edges.keys():
            self.mean[i] = statistics.mean(self.edges[i])

    def calculate_all_medians(self):
        for i in self.edges.keys():
            self.median[i] = statistics.median(self.edges[i])

class Bot:
    def __init__(self, user_name, password):
        self.user = user_name
        self.password = password
        self.session = get_session()
        self.sub = None
        self.uh = None
        self.driver = None
        self.log = []

    def write_new_data_log(self,subreddit, url, text, strat, conn):
        conn.execute('insert into log values (?,?,?,?,?, ?, ?)',(None, url,subreddit, strat,None, text,datetime.datetime.now().timestamp(),))

    def post(self, subreddit, text, comment_page_url, parent_comment_id):
        login_url = 'https://www.reddit.com/api/comment/'

        #read_url
        r = self.session.get(comment_page_url)
        soup = BeautifulSoup(r.text, "html.parser")

        thing_id = 't1_' + parent_comment_id
        c_id = '#commentreply_' + 't1_' +parent_comment_id
        r = subreddit
        uh = self.getmodhash()
        renderstyle = 'html'

        post_data = {'thing_id':thing_id,'c_id':c_id,'r':r,'uh': uh, 'renderstyle':renderstyle}
        r = self.session.post(login_url, data = post_data)
        print(post_data)
        print(r.status_code)

    def post_comment(self, subreddit, parent_url, text, strat, conn):
        try:
            self.write_new_data_log(subreddit, parent_url, text, strat, conn)
            self.post_driver(text, parent_url)
            conn.commit()
            #self.write_new_data_log(subreddit, parent_url, text, strat, conn)
            return True
        except:
            conn.rollback()
            traceback.print_exc()
            return False

    def login_driver(self):
        self.driver = webdriver.Chrome()
        self.driver.get('https://www.reddit.com/login')
        self.driver.find_element_by_id('user_login').send_keys(self.user)
        time.sleep(.5)
        self.driver.find_element_by_id('passwd_login').send_keys(self.password)
        time.sleep(.5)
        self.driver.find_element_by_id('passwd_login').send_keys(Keys.ENTER)
        time.sleep(1)

    def post_driver(self, text, parent_comment_url):
        try:
            thing_id = '#thing_t1_' + parent_comment_url.split('/')[-2]
            #print('things',parent_comment_url.split('/'))
            c_id = '#commentreply_t1_' + parent_comment_url.split('/')[-2]
            self.driver.get(parent_comment_url)
            time.sleep(5)

            '#thing_t1_dnuhvyu > div.entry.unvoted > ul > li.reply-button > a'
            self.driver.find_element_by_css_selector('li.reply-button').find_element_by_tag_name('a').click()
            time.sleep(2)
            print(c_id)
            self.driver.find_element_by_css_selector('{0} > div > div.md > textarea'.format(c_id)).send_keys(text)
            #//*[@id="commentreply_t1_dog2uk8"]/div/div[1]/textarea
            time.sleep(2)
            self.driver.find_element_by_css_selector('{0} > div > div.bottom-area > div > button.save'.format(c_id)).click()
            traceback.print_exc()
        except:
            thing_id = '#thing_t1_' + parent_comment_url.split('/')[-1]
            print('things',parent_comment_url.split('/'))
            c_id = '#commentreply_t1_' + parent_comment_url.split('/')[-1]
            self.driver.get(parent_comment_url)
            time.sleep(5)
            '#thing_t1_dnuhvyu > div.entry.unvoted > ul > li.reply-button > a'
            self.driver.find_element_by_css_selector('li.reply-button').find_element_by_tag_name('a').click()
            time.sleep(2)
            self.driver.find_element_by_css_selector('{0} > div > div.md > textarea'.format(c_id)).send_keys(text)
            time.sleep(2)
            self.driver.find_element_by_css_selector('{0} > div > div.bottom-area > div > button.save'.format(c_id)).click()

    def log_of_and_quit(self):
        self.driver.find_element_by_css_selector('#header-bottom-right > form > a').click()
        self.driver.quit()


def get_bucket(num_list, num_of_buckets, num):
    num_list.sort()
    a = np.array(num_list)
    for count, a_split in enumerate(np.array_split(a,num_of_buckets)):
        if num in a_split:
            return count

def get_percentile(num_list, num):
    num_list.sort()
    for i in num_list:
        if i >= num:
            return (num_list.index(i) + 1)/len(num_list)
    return 0

def login(session, password, user, conn):
    if (isloggedin(session, user)):
        return 1
    try:
        login_data = {'api_type':'json','op':'login','passwd':password,'user':user}
        login_url = 'https://www.reddit.com/api/login/d{0}'.format(user)
        r = session.post(login_url, data = login_data)
    except:
        session = get_session()
        traceback.print_exc()

def isloggedin(session, user):
    r = session.get('https://www.reddit.com')
    if ((user in r.text) or ("dirty_cheeser" in r.text)):
        return 1
    else:
        return 0

def comment_similarity(c1, c2):
    c1_word = list(re.split(r'[^a-zA-Z0-9]+',c1.lower()))
    c2_words = list(re.split(r'[^a-zA-Z0-9]+', c2.lower()))

    value1 = 0
    for i in c1_word:
        if i in c2_words:
            c2_words.remove(i)
    return 1 - len(c2_words)/len(list(re.split(r'[^a-zA-Z0-9]+', c2.lower())))

def split_comments_into_words(c1):
    return word_tokenize(c1.lower())

def split_comments_into_sentences(c1):
    return sent_tokenize(c1.lower())

def get_session():
    s = requests.Session()
    s.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:48.0) Gecko/20100101 Firefox/48.0'
    return s

def run_bot():
    creds=[]
    db_lock.acquire()
    conn = sqlite3.connect('reddit.db')
    rs = conn.execute('select * from reddit_logins').fetchall()
    for r in rs:
        creds.append({'user_name':r[0], 'password':r[1]})
    main_bot = Bot(creds[0]['user_name'], creds[0]['password'])
    conn.close()
    db_lock.release()
    return main_bot

def run_reader():
    global user_name
    creds=[]
    db_lock.acquire()
    conn = sqlite3.connect('reddit.db')
    rs = conn.execute('select * from reddit_logins').fetchall()
    for r in rs:
        creds.append({'user_name':r[0], 'password':r[1]})
    temp_session = get_session()
    login(temp_session, r[1], r[0], conn)
    user_name = r[0]
    main_reader = Reader(temp_session, conn)
    conn.close()
    db_lock.release()
    return main_reader

def generate_inputs( num):
    #gittins index with discount of .9
    db_lock.acquire()
    conn = sqlite3.connect('reddit.db')

    full_upvote_list = list(conn.execute('select result from log where result is not null').fetchall())
    db_list = list(conn.execute('select subreddit, strat, count(result), avg(result) from log where result is not null group by subreddit, strat').fetchall())

    cleaned_upvote_list = [i[0] for i in full_upvote_list]
    result_list1 = []
    result_list2 = []
    for i in subreddits:
        for j in range(1,num_of_strats + 1):
            found = False
            for k in db_list:
                if i == k[0] and j == k[1]:
                    found = True
                    result_list2.append((k[0], k[1],k[2], get_percentile(cleaned_upvote_list, k[3])))
            if not found:
                result_list1.append((i, j))
    random.shuffle(result_list1)

    #sorting_list = [( i[3]*(math.pow(discount_rate, i[2])),i) for i in result_list2]
    sorting_list = []
    for i in result_list2:
        sorting_list.append(( i[3]*(math.pow(discount_rate, i[2])),i))

    sorting_list.sort(key = operator.itemgetter(0), reverse = True)
    result_list2 = []
    for i in sorting_list:
        result_list2.append(i[1])
    result_list = result_list1 + result_list2
    print('full result list: ', result_list)
    print('cut result list: ', result_list[0:num])
    conn.close()
    db_lock.release()
    return result_list[0:num]

def post_available_comments(q):
    main_bot = run_bot()
    main_bot.login_driver()
    to_write_list = []
    analysis_done = False
    while not analysis_done or len(to_write_list) > 0:
        while not q.empty():
            temp = q.get()
            if temp is None:
                analysis_done = True
            else:
                to_write_list.append(temp)
        if len(to_write_list) > 0:
            db_lock.acquire()
            conn = sqlite3.connect('reddit.db')
            if main_bot.post_comment(to_write_list[0][0], to_write_list[0][1], to_write_list[0][2], to_write_list[0][3], conn):
                time.sleep(writing_sleep_time)
            to_write_list.remove(to_write_list[0])
            main_bot.driver.get('https://www.reddit.com')
            conn.close()
            db_lock.release()
        time.sleep(reddit_sleep_time)

    main_bot.log_of_and_quit()

def clean_db():
    #remove every post and comment over 30 days old for performance
    db_lock.acquire()
    conn = sqlite3.connect('reddit.db')
    min_timestamp = datetime.datetime.now().timestamp() - (30*24*60*60)
    conn.execute('delete from comment where timestamp < ?', (min_timestamp,))
    conn.commit()
    conn.execute('delete from posts where timestamp < ?', (min_timestamp,))
    conn.commit()
    conn.close()
    db_lock.release()

def analyze_and_posts(main_reader):
    q = multiprocessing.Queue()
    p = multiprocessing.Process(target=post_available_comments, args=(q,))
    p.start()
    for i in range(20):
        main_reader.update_log()
        inputs = generate_inputs(10)
        main_reader.read_all(5000)
        break
        random.shuffle(inputs)
        for j in inputs:
            print('inputs: ', j)
            results = []
            main_reader.build_graphs(j[0])
            results.extend(main_reader.run_strategy(3, j[0], j[1]))
            for k in results:
                q.put((j[0], k[0], k[1], j[1]))
                print('result added: ', (j[0], k[0], k[1], j[1]))
            main_reader.dereference_graphs(j[0])
    q.put(None)
    p.join()

def main():
    #clean_db()
    reader = run_reader()
    analyze_and_posts(reader)

if __name__ == "__main__":
    main()
