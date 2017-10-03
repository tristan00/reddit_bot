import requests
import json
import random
from bs4 import BeautifulSoup
import traceback
import sqlite3
import time

bot = None
creds = {}
sql_file = 'reddit_db.sqlite'


#put in db
rankings = {}

class post:
    def __init__(self, pid, data_url, comment_url, date_created, data_fullname, subreddit, title, score):
        self.title = title
        self.pid = pid
        self.data_url = data_url
        self.comment_url = comment_url
        self.comments = []
        self.data_fullname = data_fullname
        self.subreddit = subreddit
        self.score = score
        print('post read: ', pid, data_url, comment_url, date_created, data_fullname, subreddit, title)

    def todb(self):
        pass

class subreddit:
    def __init__(self, name):
        self.name = name
        self.posts = []


    def todb(self):
        conn = sqlite3.connect(sql_file)
        cursor = conn.cursor()
        cursor.execute('create table if not exists {0} (sub_name TEXT PRIMARY KEY)'.format('subreddit'))
        try:
            cursor.execute('insert into subreddit(sub_name) values(:sub_name)', {'sub_name': self.name})
        except:
            traceback.print_exc()
        conn.commit()

        for p in self.posts:
            p.todb()

#BOT
class bot:
    def __init__(self, bid, user_name, password):
        self.id = bid
        self.user = user_name
        self.password = password
        self.session = get_session()
        self.sub = None

    def login(self):
        while True:
            time.sleep(5)
            try:
                print(self.user, self.password)
                login_data = {'api_type':'json','op':'login','passwd':self.password,'user':self.user}
                login_url = 'https://www.reddit.com/api/login/d{0}'.format(self.user)
                r = self.session.post(login_url, data = login_data)
                r = self.session.get('https://www.reddit.com')
                #write_to_file(self.user, r.text)
                break
            except:
                self.session = get_session()
                traceback.print_exc()


def create_bots():
    global creds
    conn = sqlite3.connect('reddit.db')
    c = conn.cursor()
    rs = c.execute('select * from reddit_logins').fetchall()
    print(1)
    for r in rs:
        print(r)
        creds[r[0]] = {'user_name':r[2], 'password':r[1]}
    conn.close()

    global bots
    for i in creds.keys():
        print(i)
        bots.append(bot(i, creds[i]['user_name'], creds[i]['password']))

    for b in bots:
        print(b, ' login')
        b.login()

def get_word_weighting():
    global rankings
    conn = sqlite3.connect('reddit.db')
    c = conn.cursor()
    rs = c.execute('select * from key_words').fetchall()
    for r in rs:
        rankings[r[0]] = r[1]
    conn.close()


def get_session():
    s = requests.Session()
    s.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:48.0) Gecko/20100101 Firefox/48.0'
    return s

def write_to_file(user, r_text):
    #r_text
    f = open('{0}.html'.format(user), 'w')
    f.write(r_text.encode('ascii', 'ignore'))
    f.close()

def main():
    global p_list
    get_word_weighting()
    create_bots()

    print(len(bots))
    for b in bots:
        b.execute_strategy1('all', 1)
        time.sleep(random.randint(5,30))


main()
