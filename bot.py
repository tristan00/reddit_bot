import requests
import json
import random
from bs4 import BeautifulSoup
import traceback
import sqlite3
import time

bot = None
creds = []
sql_file = 'reddit_db.sqlite'
bots = []

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
        try_counter = 3
        while try_counter >0:
            time.sleep(5)
            try:
                print(self.user, self.password)
                login_data = {'api_type':'json','op':'login','passwd':self.password,'user':self.user}
                login_url = 'https://www.reddit.com/api/login/d{0}'.format(self.user)
                r = self.session.post(login_url, data = login_data)
                time.sleep(1)
                r = self.session.get('https://www.reddit.com')

                if (self.user in r.text):
                    return 1
                break
            except:
                self.session = get_session()
                traceback.print_exc()
                try_counter =- 1
        return 0

    def post(self, text):
        pass


def create_bots():
    global creds
    conn = sqlite3.connect('reddit.db')
    c = conn.cursor()
    rs = c.execute('select * from reddit_logins').fetchall()
    print(1)
    for r in rs:
        print(r)
        creds.append({'user_name':r[0], 'password':r[1]})
    conn.close()

    global bots
    for i in creds:
        print(i)

        bots.append(bot(i, i['user_name'], i['password']))

    for b in bots:
        print(b, ' attempting login')
        if (b.login() == 1):
            print('login succesful')
        else:
            print('login failure')

def get_session():
    s = requests.Session()
    s.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:48.0) Gecko/20100101 Firefox/48.0'
    return s

def main():
    global p_list
    create_bots()




main()
