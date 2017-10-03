import requests
import json
import random
from bs4 import BeautifulSoup
import traceback
import sqlite3
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys


main_bot = None
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
        self.uh = None
        self.driver = webdriver.Chrome()

    def login(self):
        try_counter = 3
        while try_counter >0:
            if (self.isloggedin()):
                return 1
            try:
                print(self.user, self.password)
                #login_data = {'api_type':'json','op':'login','passwd':self.password,'user':self.user}

                login_data = {'api_type':'json','op':'login','passwd':self.password,'user':"dirty_cheeser"}
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
        if ((self.user in r.text) or ("dirty_cheeser" in r.text)):
            return 1
        else:
            return 0

    def post(self, subreddit, text, comment_page_url, parent_comment_id):
        login_url = 'https://www.reddit.com/api/comment/'

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


    #temporary

    def post_comment(self, parent_url, text):
        self.login_driver()
        self.post_driver(text, parent_url)
        self.log_of_and_quit()

    def login_driver(self):
        self.driver.get('https://www.reddit.com/login')
        self.driver.find_element_by_id('user_login').send_keys(self.user)
        time.sleep(.5)
        self.driver.find_element_by_id('passwd_login').send_keys(self.password)
        time.sleep(.5)
        self.driver.find_element_by_id('passwd_login').send_keys(Keys.ENTER)
        time.sleep(1)

    def post_driver(self, text, parent_comment_url):
        thing_id = '#thing_t1_' + parent_comment_url.split('/')[-2]
        c_id = '#commentreply_t1_' + parent_comment_url.split('/')[-2]
        self.driver.get(parent_comment_url)
        '#thing_t1_dnuhvyu > div.entry.unvoted > ul > li.reply-button > a'
        self.driver.find_element_by_css_selector(thing_id + ' > div.entry.unvoted > ul > li.reply-button > a').click()
        time.sleep(2)
        self.driver.find_element_by_css_selector(c_id + ' > div > div.md > textarea').send_keys(text)
        time.sleep(2)
        self.driver.find_element_by_css_selector(c_id + ' > div > div.bottom-area > div > button.save').click()
        time.sleep(2)

    def log_of_and_quit(self):
        self.driver.find_element_by_css_selector('#header-bottom-right > form > a').click()
        self.driver.quit()



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

def get_session():
    s = requests.Session()
    s.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:48.0) Gecko/20100101 Firefox/48.0'
    return s

def main():
    global main_bot
    create_bots()
    main_bot.post_comment('https://www.reddit.com/r/howdoesredditwork/comments/7408zb/test4/dnuhvyu/', 'test9')

main()
