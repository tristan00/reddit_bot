#to do
#add parent pointer in comment data
#add reporting functionlity
#implement soluition 1
#switch data analysis to panda
#add strategy picking functionalioty
#generalize comment reading



import requests
import json
import random
from bs4 import BeautifulSoup
import traceback
import sqlite3
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import re
import datetime
import statistics

main_bot = None
creds = []
sql_file = 'reddit_db.sqlite'
bots = []


subreddits = ['worldnews', 'gonewild', 'nsfw', 'funny', 'aww', 'pics', 'wtf','ImGoingToHellForThis', 'NSFW_GIF', 'news']

class reader():
    def __init__(self, subreddit, session):
        self.name = subreddit
        self.put_sub_to_db()
        self.session = session
        self.write_posts_and_comments_to_db()
        #self.read_all()

        self.word_dict = {}
        self.sentence_dict = {}
        self.sentence_count_dict = {}
        self.pick_strategy_and_sub()


    def read_all(self):
        temp = self.name
        for i in subreddits:
            self.name = i
            self.write_posts_and_comments_to_db()
        self.name = temp

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
        cursor = conn.cursor()

        r = self.session.get('https://www.reddit.com/r/{0}/'.format(self.name))
        soup = BeautifulSoup(r.text, "html.parser")

        posts = soup.find('div', {'id':'siteTable'}).find_all('div', {'data-whitelist-status':'all_ads'}, recursive = False)

        print(len(posts))
        for p in posts:
            self.write_post(conn, p)
        conn.commit()
        conn.close()
        print('writing posts done')

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

                    conn.execute('insert into comment values(?,?,?,?, ?,?)', (p[1].split('_')[0], comment_id.split('_')[1], parent_id,comment_date.timestamp(), comment_text,  comment_upvotes))
                    print('inserted comment:', (p[1].split('_')[0], comment_id.split('_')[1], parent_id,comment_date.timestamp(), comment_text,  comment_upvotes))
                    conn.commit()

                except:
                    pass
                    #traceback.print_exc()

        except:
            traceback.print_exc()

    def write_posts_and_comments_to_db(self):
        conn = sqlite3.connect('reddit.db')
        self.get_post_list()

        res = conn.execute('select distinct data_permalink, post_id from posts')
        for p in res:
            #continue
            time.sleep(3)
            print(p)
            self.write_comments(p,conn)

        print('writing comments done')

        conn.commit()
        conn.close()

    def strategy1(self):
        comment_min_len = 10
        min_comments = 2
        comment_words = None
        comment_to_respond_to = None
        comment_to_respond_to_text= None

        #pick post, new post with high upvotes
        conn = sqlite3.connect('reddit.db')
        r = self.session.get('https://www.reddit.com/r/{0}/rising'.format(self.name))
        soup = BeautifulSoup(r.text,'html.parser')
        ps = soup.find('div', {'id':'siteTable'}).find_all('div', {'data-whitelist-status':'all_ads'}, recursive = False)

        p_url = None
        p_id = None

        return_value= None
        for p in ps:
            post_data = self.write_post(conn, p)
            p_url = post_data[3]
            p_id = post_data[0]

            print('p_id, P_url:', p_id, p_url)
            if p_url is None or p_id is None:
                continue

            #pick comment, second earliest since earliest is often mod post
            r = self.session.get('https://www.reddit.com' + p_url)
            comment_table = soup.find('div', {'class':'sitetable nestedlisting'})
            comments = comment_table.find_all('div', {'class': re.compile("entry unvoted.*")})
            print('num of comments: ', len(comments))
            if len(comments) < min_comments:
                return_value = 'Not enough comments'
                continue
            else:
                return_value = None


            comment_dict = {}
            earliest_comment_timestamp = None
            second_earliest_comment_timestamp = None
            for c in comments:
                try:
                    print('atributes: ', c.attrs)
                    print('html: ', c)
                    print('text len: ',len(c.find('div', {'class':'md'}).text.lower()))
                    if len(c.find('div', {'class':'md'}).text.lower()) < comment_min_len:
                        continue

                    time_str = c.find('time')['datetime']
                    comment_timestamp = datetime.datetime.strptime(time_str,'%Y-%m-%dT%H:%M:%S+00:00').timestamp()
                    if earliest_comment_timestamp is None:
                        earliest_comment_timestamp = comment_timestamp
                    elif second_earliest_comment_timestamp is None and comment_timestamp > earliest_comment_timestamp:
                        second_earliest_comment_timestamp = comment_timestamp
                    elif second_earliest_comment_timestamp is None and comment_timestamp < earliest_comment_timestamp:
                        second_earliest_comment_timestamp = earliest_comment_timestamp
                        earliest_comment_timestamp = comment_timestamp

                    comment_dict[comment_timestamp] = c
                except:
                    traceback.print_exc()


            comment_to_respond_to = comment_dict[earliest_comment_timestamp]

            comment_to_respond_to_text= comment_to_respond_to.find('div', {'class':'md'}).text.lower()
            comment_to_respond_to_text = comment_to_respond_to_text.replace(r'\n','.')
            comment_words = re.split('[.!?]+',comment_to_respond_to_text)
            break


        #run dict maker only accepting sentences that share words with title and/or post
        print(p_url, p_id, comment_to_respond_to_text)

        if p_url is None or p_id is None:
            return_value = 'null pid'
            return

        res = conn.execute('select distinct comment.comment_id, comment.post_id, comment.text, comment.upvotes from posts join comment on posts.post_id = comment.post_id where subreddit = ?', (self.name,))

        for r in res:
            text_post = r[2].replace(r'\n','.')
            text_post = text_post.lower()
            relevant = False
            for w in comment_words:
                if w in text_post:
                    relevant = True
            if relevant:
                continue

            sentences = re.split('[.!?]*',text_post)

            sentences2 = []
            for s in sentences:
                if len(s) >1:
                    sentences2.append(s)

            for s in sentences2:
                normalized_sentence = s.lower()
                if normalized_sentence in self.sentence_dict.keys():
                    self.sentence_dict[normalized_sentence] = self.sentence_dict[normalized_sentence].append(int(r[3]))
                else:
                    self.sentence_dict[normalized_sentence] = [int(r[3])]

        current_comment = None
        max_median = 0
        for i in self.sentence_dict.keys():
            self.sentence_dict[i] = (self.sentence_dict[i][0],self.sentence_dict[i][1],self.sentence_dict[i][1]/self.sentence_dict[i][0])
            if(max_median < statistics.median(self.sentence_dict[i]) and len(self.sentence_dict[i]) > 5):
                max_median = statistics.median(self.sentence_dict[i])
                print(i, self.sentence_dict[i])
                current_comment = i

        print('median: ', statistics.median(self.sentence_dict[i]), current_comment)
        print('current comment text:', current_comment)
        print('p_id:',p_id)
        print('parent comment:', comment_to_respond_to_text)
        #put optimal number of sentences and post it as response

    def pick_strategy_and_sub(self):
        print(self.strategy1())

class bot:
    def __init__(self, bid, user_name, password):
        self.id = bid
        self.user = user_name
        self.password = password
        self.session = get_session()
        self.sub = None
        self.uh = None
        self.driver = None

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
        self.driver = webdriver.Chrome()
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
    main_bot.login()
    main_reader = reader('funny', main_bot.session)


    #main_reader.write_posts_and_comments_to_db()

    #main_bot.post_comment('https://www.reddit.com/r/howdoesredditwork/comments/7408zb/test4/dnuhvyu/', 'test9')

main()
