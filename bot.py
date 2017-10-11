#bug fixes, strategy1
#find out why there are so many nulls in pids
#find out why it jumps out of the comments.

#to do:
#generalize post reading funtionality
#get log to update
#switch data analysis to panda
#add strategy picking functionalioty

import requests
import json
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import os
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

reddit_sleep_time = 3
main_bot = None
sql_file = 'reddit_db.sqlite'
os.chdir(os.path.dirname(os.path.realpath(__file__)))
subreddits = ['dankmemes', 'me_irl', 'surrealmemes', 'DeepFriedMemes', 'totallynotrobots']
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

    def toDB(self, conn):
        try:
            conn.execute('insert into comment values(?,?,?,?, ?,?)', (self.p_id.split('_')[0], self.comment_id.split('_')[1], self.parent_id, self.comment_timestamp, self.text,  self.comment_upvotes))
            print('inserted comment:', (self.p_id.split('_')[0], self.comment_id.split('_')[1], self.parent_id, self.comment_timestamp, self.text,  self.comment_upvotes))
            conn.commit()
        except:
            try:
                conn.execute('update comment set upvotes = ? where comment_id = ?', (self.comment_upvotes, self.comment_id.split('_')[1],))
                print('updated comment:', (self.p_id.split('_')[0], self.comment_id.split('_')[1], self.parent_id, self.comment_timestamp, self.text,  self.comment_upvotes))
                conn.commit()
            except:
                traceback.print_exc()

class reader():
    def __init__(self, session):
        self.name = ""
        self.put_sub_to_db()
        self.session = session
        #self.write_posts_and_comments_to_db()

        self.word_dict = {}
        self.sentence_count_dict = {}
        self.g_comments = None
        self.g_title = None
        self.g_words = None

        self.possible_comments = {}

    def read_all(self, count):
        for i in subreddits:
            print('reading posts in :', i)
            self.get_post_list(i)
        self.write_comments_to_db(count)

    def put_sub_to_db(self):
        conn = sqlite3.connect('reddit.db')
        cursor = conn.cursor()

        #TODO: create initial db creation code
        cursor.execute('create table if not exists {0} (sub_name TEXT PRIMARY KEY)'.format('subreddit'))
        cursor.execute('create table if not exists {0} (subreddit TEXT, post_id TEXT UNIQUE, post_title TEXT, timestamp TEXT, data_permalink TEXT, comment_count int, upvotes int)'.format('posts'))
        cursor.execute('create table if not exists {0} (post_id TEXT, comment_id TEXT PRIMARY KEY, parent_id TEXT, timestamp TEXT, text TEXT, upvotes int)'.format('comment'))

        conn.commit()
        conn.close()

    def write_post(self, conn, p):
        #print(p.attrs)
        try:
            print('Inserting post:', p['data-fullname'].split('_')[1], p.find('p',{'class':'title'}).find('a').text, p['data-timestamp'], p['data-permalink'], None, None)
            try:
                conn.execute('insert into posts values(?,?,?,?,?,?,?)', (self.name ,p['data-fullname'].split('_')[1], p.find('p',{'class':'title'}).find('a').text, p['data-timestamp'], p['data-permalink'], 0, 0) )
            except:
                pass
            return (p['data-fullname'].split('_')[1], p.find('p',{'class':'title'}).find('a').text, p['data-timestamp'], p['data-permalink'], None, None)
        except:
            traceback.print_exc()
            return (None, None, None, None, None, None)

    def get_post_list(self, subreddit):
        conn = sqlite3.connect('reddit.db')
        tries = 3
        while tries >0:
            time.sleep(reddit_sleep_time)
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
            return
        comment_soup = soup.find_all('div', {'class': re.compile("entry unvoted.*")})
        comment_list = []
        for c in comment_soup:
            try:
                temp_c = comment_data(c, p_id)
                temp_c.read_all_parameters()
                temp_c.toDB(conn)
            except:
                pass
                #traceback.print_exc()

    def write_comments_to_db(self, count):
        conn = sqlite3.connect('reddit.db')
        res = list(conn.execute('select distinct data_permalink, post_id from posts order by timestamp desc').fetchall())
        random.shuffle(res)
        #res = conn.execute('select distinct data_permalink, post_id from posts')
        if count is None:
            count = len(res)
        for p in res[0:count]:
            time.sleep(reddit_sleep_time)
            print(p)
            self.write_comments(p[0], p[1],conn)

        print('writing comments done')
        conn.commit()
        conn.close()

    def build_response_graph(self, graph_type):
        #graph types:
        #1: analyzes comment response words
        #2: analyzes title words

        if (graph_type == 1):
            g = response_word_graph(2)
        elif (graph_type == 2):
            g = response_word_graph(2)
        elif (graph_type == 3):
            g = response_word_graph(0)
        else:
            g = response_word_graph(0)
        conn = sqlite3.connect('reddit.db')
        res = conn.execute('select distinct a.comment_id, a.parent_id, a.post_id, a.text, a.upvotes, b.text, a.timestamp, a.post_id from comment a join comment b on a.parent_id = b.comment_id order by a.timestamp')

        for r in res:
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
                        g.add_item(j, i, int(r[4]))
                    except:
                        traceback.print_exc()
        conn.close()
        return g

    def build_graphs(self):
        print('building graphs')
        self.g_words = self.build_response_graph(1)
        self.g_title = self.build_response_graph(2)
        self.g_comments = self.build_response_graph(3)

    def get_new_posts_ready_to_analyze(self, conn, subreddit):
        comment_min_len = 10
        min_comments = 2
        posts_to_analyze = 100
        r = self.session.get('https://www.reddit.com/r/{0}/top/?sort=top&t=hour'.format(subreddit))
        soup = BeautifulSoup(r.text,'html.parser')
        ps = soup.find('div', {'id':'siteTable'}).find_all('div', {'data-whitelist-status':'all_ads'}, recursive = False)

        posts = []
        for p in enumerate(ps[:posts_to_analyze]):
            post_data = self.write_post(conn, p[1])
            p_url = post_data[3]
            p_id = post_data[0]
            temp_post = post(p_url, p_id)

            print(p[0],' p_id, P_url:', p_id, p_url)
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


    def strategy2(self, subreddit, max_results):
        results = []
        conn = sqlite3.connect('reddit.db')
        posts = self.get_new_posts_ready_to_analyze(conn, subreddit)
        possible_comment_list = self.get_possible_comment_list(subreddit, conn)

        for p in posts:
            for c in p.comments:
                comment_id = c.soup.find('input', {'name':'thing_id'})['value'].split('_')[1]
                if p.url is None or p.p_id is None:
                    continue
                sorting_structure = []
                for r in possible_comment_list:
                    implied_reply_score = self.g_comments.values_statement_by_mean([c.text], [r[2]])
                    if 'http' not in r[2]:
                        sorting_structure.append((r[0], r[4], implied_reply_score*implied_reply_score, r[2]))
                sorting_structure.sort(key=operator.itemgetter(2), reverse=True)
                current_comment = sorting_structure[0]
                try:
                    if current_comment[2] > 0:
                        print('returning:', ('https://www.reddit.com'+ p.url + comment_id, current_comment[3], current_comment[2]))
                        #put optimal number of sentences and post it as response
                        results.append(('https://www.reddit.com'+ p.url + comment_id, current_comment[3], current_comment[2]))#full url, text, expected value
                except:
                    traceback.print_exc()
                if len(results) >=max_results:
                    results.sort(key=operator.itemgetter(2), reverse=True)
                    return results
        results.sort(key=operator.itemgetter(2), reverse=True)
        conn.close()
        return results

    def strategy1(self, subreddit, max_results):
        results = []
        conn = sqlite3.connect('reddit.db')
        posts = self.get_new_posts_ready_to_analyze(conn, subreddit)
        possible_comment_list = self.get_possible_comment_list(subreddit, conn)

        for p in posts:
            for c in p.comments:
                comment_id = c.soup.find('input', {'name':'thing_id'})['value'].split('_')[1]
                if p.url is None or p.p_id is None:
                    continue
                sorting_structure = []
                for r in possible_comment_list:
                    implied_reply_score = self.g_words.values_statement_by_median(split_comments_into_words(c.text), split_comments_into_words(r[2]))
                    implied_title_score = self.g_title.values_statement_by_median(split_comments_into_words(c.text),split_comments_into_words(r[6]))
                    implied_sentence_score = self.g_comments.values_statement_by_median(split_comments_into_sentences(c.text),split_comments_into_sentences(r[2]))
                    if 'http' not in r[2]:
                        sorting_structure.append((r[0], r[4], math.pow((implied_reply_score*implied_reply_score) + (implied_title_score*implied_title_score) + (implied_sentence_score*implied_sentence_score), 1/3), r[2]))

                sorting_structure.sort(key=operator.itemgetter(2), reverse=True)
                current_comment = sorting_structure[0]

                try:
                    if current_comment[2] > 0:
                        print('returning:', ('https://www.reddit.com'+ p.url + comment_id, current_comment[3], current_comment[2]))
                        #put optimal number of sentences and post it as response
                        results.append(('https://www.reddit.com'+ p.url + comment_id, current_comment[3], current_comment[2]))#full url, text, expected value
                except:
                    traceback.print_exc()
                if len(results) >=max_results:
                    results.sort(key=operator.itemgetter(2), reverse=True)
                    return results
        results.sort(key=operator.itemgetter(2), reverse=True)
        conn.close()
        return results

    def run_strategy(self, num, subreddit, strat):
        results = []
        try:
            if(strat == 1):
                results = self.strategy1(subreddit, 10*num)
            elif (strat == 2):
                results = self.strategy2(subreddit, 10*num)
            print('Results:')
            for i in results:
                print(i)
        except:
            traceback.print_exc()
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

class node():
    def __init__(self, content, min_results_per_node):
        self.min_length = min_results_per_node
        self.max_length = 1000
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

class bot:
    def __init__(self, user_name, password):
        self.user = user_name
        self.password = password
        self.session = get_session()
        self.login()
        self.sub = None
        self.uh = None
        self.driver = None
        self.main_reader = reader(self.session)

        self.main_reader.read_all(1000)
        self.login_driver()
        self.main_reader.build_graphs()

        for s in subreddits:
            self.results = []
            self.results.extend(self.main_reader.run_strategy(1,s, 1))
            print('Results: ', self.results)
            for j in self.results:
                self.post_comment(s, j[0], j[1], 1)
                time.sleep(90)
            self.results = []
            self.results.extend(self.main_reader.run_strategy(1,s, 2))
            print('Results: ', self.results)
            for j in self.results:
                self.post_comment(s, j[0], j[1], 2)
                time.sleep(90)


        self.log_of_and_quit()

    def write_new_data_log(self,subreddit, url, text, strat):
        parent_url = url
        conn = sqlite3.connect('reddit.db')
        conn.execute('create table if not exists {0} (url TEXT, parent_url text primary key, subreddit text, strat int, result int)'.format('log'))
        conn.execute('insert into log values (?,?,?,?,?)',(None, url,subreddit, strat,None))
        conn.close()

    def login(self):

        if (self.isloggedin()):
            return 1
        try:
            login_data = {'api_type':'json','op':'login','passwd':self.password,'user':self.user}
            login_url = 'https://www.reddit.com/api/login/d{0}'.format(self.user)
            r = self.session.post(login_url, data = login_data)
        except:
            self.session = get_session()
            traceback.print_exc()

    def getmodhash(self):
        r = self.session.get('https://www.reddit.com/api/me.json')
        j = json.loads(r.text)
        return j['data']['modhash']

    def isloggedin(self):
        r = self.session.get('https://www.reddit.com')
        soup = BeautifulSoup(r.text, "html.parser")
        #self.uh = soup.find('input',{'name':'uh', 'type':'hidden'})['value']
        if ((self.user in r.text) or ("dirty_cheeser" in r.text)):
            return 1
        else:
            return 0

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

    def post_comment(self, subreddit, parent_url, text, strat):
        self.post_driver(text, parent_url)
        self.write_new_data_log(subreddit, parent_url, text, strat)

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
            try:
                self.driver.find_element_by_css_selector(thing_id + ' > div.entry.unvoted > ul > li.reply-button > a').click()
            except:
                try:
                    self.driver.find_element_by_css_selector(thing_id + ' > div.entry.likes.RES-keyNav-activeElement > ul > li.reply-button > a').click()
                except:
                    self.driver.find_element_by_css_selector(thing_id + ' > div.entry.unvoted > ul > li.reply-button').find_element_by_tag_name('a').click()

            time.sleep(2)
            self.driver.find_element_by_css_selector(c_id + ' > div > div.md > textarea').send_keys(text)
            time.sleep(2)
            self.driver.find_element_by_css_selector(c_id + ' > div > div.bottom-area > div > button.save').click()
        except:
            thing_id = '#thing_t1_' + parent_comment_url.split('/')[-1]
            print('things',parent_comment_url.split('/'))
            c_id = '#commentreply_t1_' + parent_comment_url.split('/')[-1]
            self.driver.get(parent_comment_url)
            '#thing_t1_dnuhvyu > div.entry.unvoted > ul > li.reply-button > a'
            try:
                self.driver.find_element_by_css_selector(thing_id + ' > div.entry.unvoted > ul > li.reply-button > a').click()
            except:
                try:
                    self.driver.find_element_by_css_selector(thing_id + ' > div.entry.likes.RES-keyNav-activeElement > ul > li.reply-button > a').click()
                except:
                    self.driver.find_element_by_css_selector(thing_id + ' > div.entry.unvoted > ul > li.reply-button').find_element_by_tag_name('a').click()

            time.sleep(2)
            self.driver.find_element_by_css_selector(c_id + ' > div > div.md > textarea').send_keys(text)
            time.sleep(2)
            self.driver.find_element_by_css_selector(c_id + ' > div > div.bottom-area > div > button.save').click()

        time.sleep(2)

    def log_of_and_quit(self):
        self.driver.find_element_by_css_selector('#header-bottom-right > form > a').click()
        self.driver.quit()

    def buildGittins(self):
        pass

def comment_similarity(c1, c2):
    c1_word = list(re.split(r'[^a-zA-Z0-9]+',c1.lower()))
    c2_words = list(re.split(r'[^a-zA-Z0-9]+', c2.lower()))

    value1 = 0
    for i in c1_word:
        if i in c2_words:
            c2_words.remove(i)

    return 1 - len(c2_words)/len(list(re.split(r'[^a-zA-Z0-9]+', c2.lower())))

def split_comments_into_words(c1):
    c1_word = list(re.split(r"[ \n]+", c1.lower()))

    res = []
    value1 = 0
    for i in c1_word:
        if len(i)>2:
            res.append(i)
    return res

def split_comments_into_sentences(c1):
    c1_word = list(re.split(r"[.!?]+", c1.lower()))

    res = []
    value1 = 0
    for i in c1_word:
        if len(i)>2:
            res.append(i)
    return res

def get_session():
    s = requests.Session()
    s.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:48.0) Gecko/20100101 Firefox/48.0'
    return s

def run_bot():
    creds=[]
    conn = sqlite3.connect('reddit.db')
    rs = conn.execute('select * from reddit_logins').fetchall()
    for r in rs:
        creds.append({'user_name':r[0], 'password':r[1]})
    main_bot = bot(creds[0]['user_name'], creds[0]['password'])
    conn.close()

def main():
    global main_bot
    run_bot()

if __name__ == "__main__":
    main()