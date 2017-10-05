#to do
#find out why it repeats solutions
#add commenting updates
#get log to update
#switch data analysis to panda
#add strategy picking functionalioty

import requests
import json
import random
from bs4 import BeautifulSoup
import traceback
import sqlite3
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import analysis
import os

main_bot = None
creds = []
sql_file = 'reddit_db.sqlite'
bots = []

os.chdir(os.path.dirname(os.path.realpath(__file__)))

strategies = [1]

class bot:
    def __init__(self, bid, user_name, password):
        self.id = bid
        self.user = user_name
        self.password = password
        self.session = get_session()
        self.login()

        self.sub = None
        self.uh = None
        self.driver = None

        self.main_reader = analysis.reader(self.session)

        for i in range(1):
            self.results = []
            #self.main_reader.read_all()
            self.main_reader.reset_subreddit()
            self.results.extend(self.main_reader.pick_strategy_and_sub(1))
            for j in self.results:
                print(self.results)
                self.post_comment(self.results[0][0], self.results[0][1])
                time.sleep(600)
        #self.post_comment('https://www.reddit.com/r/howdoesredditwork/comments/7408zb/test4/dnunezd/', 'test99')

    def write_new_data_log(self,url, text):
        parent_url = url
        conn = sqlite3.connect('reddit.db')
        conn.execute('create table if not exists {0} (url TEXT, parent_url text primary key, subreddit text, strat int, result int)'.format('log'))
        conn.execute('insert into log values (?,?,?,?,?)',(None, url,self.main_reader.name, 1,None))
        conn.close()

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
        self.driver = webdriver.Chrome()
        self.login_driver()
        self.post_driver(text, parent_url)
        self.log_of_and_quit()
        self.write_new_data_log(parent_url, text)
        #conn = sqlite3.connect('reddit.db')
        #conn.execute('create table if not exists {0} (url TEXT, subreddit text, strat int, result int)'.format('log'))
        #conn.execute('insert into log values (?,?,?,?)', (parent_url,,?,?))

    def login_driver(self):
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
            print('things',parent_comment_url.split('/'))
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



def create_bots():
    global creds
    global main_bot
    global bots

    conn = sqlite3.connect('reddit.db')
    rs = conn.execute('select * from reddit_logins').fetchall()
    for r in rs:
        print(r)
        creds.append({'user_name':r[0], 'password':r[1]})
    for i in creds:
        print(i)
        main_bot = bot(i, i['user_name'], i['password'])
        bots.append(main_bot)
    conn.close()



def get_session():
    s = requests.Session()
    s.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:48.0) Gecko/20100101 Firefox/48.0'
    return s

def main():
    global main_bot
    try:
        create_bots()
    except:
        traceback.print_exc()

if __name__ == "__main__":
    main()
