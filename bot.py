import requests
import json
import random
from bs4 import BeautifulSoup
import traceback
import sqlite3
import time

main_bot = None
creds = []
sql_file = 'reddit_db.sqlite'
bots = []

#put in db
rankings = {}

class

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
        self.uh = None

    def login(self):
        try_counter = 3
        while try_counter >0:
            if (self.isloggedin()):
                return 1
            try:
                print(self.user, self.password)
                login_data = {'api_type':'json','op':'login','passwd':self.password,'user':self.user}
                login_url = 'https://www.reddit.com/api/login/d{0}'.format(self.user)
                r = self.session.post(login_url, data = login_data)
                time.sleep(1)
            except:
                self.session = get_session()
                traceback.print_exc()
                try_counter =- 1
        return 0

    def getmodhash(self):
        r = self.session.get('https://www.reddit.com/api/me.json')
        j = json.loads(r.text)
        return j['data']['modhash']


    def isloggedin(self):
        r = self.session.get('https://www.reddit.com')
        soup = BeautifulSoup(r.text, "html.parser")
        #self.uh = soup.find('input',{'name':'uh', 'type':'hidden'})['value']
        if (self.user in r.text):
            return 1
        else:
            return 0


    def post(self, subreddit, text, comment_page_url, parent_comment_id):
        login_url = 'https://www.reddit.com/api/comment'

        #read_url
        r = self.session.get(comment_page_url)

        soup = BeautifulSoup(r.text, "html.parser")

        #thing_id=t1_dnufe8gtext=test43id=#commentreply_t1_dnufe8gr=howdoesredditworkuh=i8fn7btghc6e4f0adb3d2bfdf873256a51885084700a01b562renderstyle=html
        #{'uh': 'hdzjn9f7i4d15e53e581e90c831a42a60359024e8e77091895', 'thing_id': 't1_dnufe8g', 'r': 'howdoesredditwork', 'c_id': '#commentreply_t1_dnufe8g', 'renderstyle': 'html'}

        thing_id = 't1_' + parent_comment_id
        c_id = '#commentreply_' + 't1_' +parent_comment_id
        r = subreddit
        uh = self.getmodhash()
        renderstyle = 'html'

        post_data = {'thing_id':thing_id,'c_id':c_id,'r':r,'uh': uh, 'renderstyle':renderstyle}
        r = self.session.post(login_url, data = post_data)
        print(post_data)
        print(r.status_code)

def create_bots():
    global creds
    global main_bot
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
        main_bot = bot(i, i['user_name'], i['password'])
        bots.append(main_bot)

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
    global main_bot
    create_bots()
    main_bot.post('howdoesredditwork', 'test45', 'https://www.reddit.com/r/howdoesredditwork/comments/7408zb/test4/','dnufyvt')



main()
