import requests
import json
import random
from bs4 import BeautifulSoup
import traceback
import sqlite3
import time

bots = []
p_list = []
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
                login_data = {'api_type':'json','op':'login','passwd':self.password,'user':self.user}
                login_url = 'https://www.reddit.com/api/login/d{0}'.format(self.user)
                r = self.session.post(login_url, data = login_data)
                r = self.session.get('https://www.reddit.com')
                #write_to_file(self.user, r.text)
                break
            except:
                self.session = get_session()
                traceback.print_exc()

    def upvote_post(self, post):
        self.session.post('https://www.reddit.com/api/vote?dir={0}&id={1}&sr={2}'.format(1, post.data_fullname, post.subreddit))

    def downvote_post(self, post):
        self.session.post('https://www.reddit.com/api/vote?dir={0}&id={1}&sr={2}'.format(-1, post.data_fullname, post.subreddit))

    def read_subreddit(self, sub_name):
        try:
            url = 'https://www.reddit.com/r/{0}/new/'.format(sub_name)
            s = self.session
            r = s.get(url)
            soups = BeautifulSoup(r.text,"html.parser")
            print(r.text)

            subreddit_data = subreddit(sub_name)

            print('number of posts: ', len(soups.find('div',{'class':'sitetable linklisting'}).find_all('div',{'data-subreddit':sub_name})))

            for soup in soups.find('div',{'class':'sitetable linklisting'}).find_all('div',{'data-subreddit':sub_name}):
                title = ' '.join(soup.find('p', {'class':'title'}).text.split())
                data_fullname = soup['data-fullname']
                pid = soup['id']
                data_url = soup['data-url']
                comment_soup = list(soup.find('ul', {'class':'flat-list buttons'}).find_all('li'))[0]
                comment_url = comment_soup.find('a')['href']
                try:
                    score = int(soup.find('div', {'class':'score unvoted'}).text)
                except:
                    score = None
                print('read: ', pid, data_url, comment_url, None, data_fullname, sub_name, title,score)
                subreddit_data.posts.append(post(pid, data_url, comment_url, None, data_fullname, sub_name, title,score))
                #pid, data_url, comment_url, date_created, data_fullname, subreddit)

            self.sub = subreddit_data.posts
        except:
            traceback.print_exc()

    def vote(self):
        posts = {}
        min_points = 0
        max_points= 0

        print(len(self.sub))
        for p in self.sub:
            points = 0
            for k in rankings.keys():
                if k in p.title.lower():
                    points += rankings[k]
            if min_points > points:
                min_points = points
            if max_points < points:
                max_points = points
            posts[p] = points
            print(points, p.title)

        print('')

        print('')
        max_score = 0
        print('max')
        for p in posts.keys():
            if posts[p] == max_points:
                print(posts[p], p.score, p.title)
                if p.score is not None and max_score < p.score:
                    max_score = p.score

        for p in posts.keys():
            if max_score == p.score and posts[p] == max_points:
                if random.randint(0,max_score) < random.randint(0,p.score):
                    self.upvote_post(p)
                    print('upvoted: ', posts[p], p.score, p.title)
                    time.sleep(5)

        max_score = 1000
        print('')
        print('min')
        for p in posts.keys():
            if posts[p] == min_points:
                print(posts[p],p.score,  p.title)
                if p.score is not None and max_score > p.score:
                    max_score = p.score

        for p in posts.keys():
            if max_score == p.score and posts[p] == min_points:
                print(len(bots))
                if random.randint(0,max_score) < random.randint(0,p.score):
                    self.downvote_post(p)
                    print('downvoted: ', posts[p], p.score, p.title)
                    time.sleep(5)

    def execute_strategy1(self, sub, num):
        self.read_subreddit(sub)
        time.sleep(3)
        self.vote()

def create_bots():
    global creds
    conn = sqlite3.connect('reddit.db')
    c = conn.cursor()
    rs = c.execute('select * from reddit_logins').fetchall()
    print(1)
    for r in rs:
        print(r)
        creds[r[0]] = {'user_name':r[1], 'password':r[2]}
    conn.close()

    global bots
    for i in creds.keys():
        print(i)
        bots.append(bot(i, creds[i]['user_name'], creds[i]['password']))

    for b in bots:
        b.login()

def get_word_weighting():
    global rankings
    conn = sqlite3.connect('reddit.db')
    c = conn.cursor()
    rs = c.execute('select * from key_words').fetchall()
    for r in rs:
        rankings[r[0]] = r[1]
    conn.close()

#proxies
def getProxylist():
    proxy_url = 'https://panel.limeproxies.com/client-api/get-json.php?user=user-19084&key=58c726ad62def9e2783f278dc6ef0d12e8cd2e46'
    gp_url = 'http://ghostproxies.com/proxies/api/dhhua.json'
    proxy_list = []
    error_list = []
    counter = 0

    global p_list

    try:
        response = requests.get(proxy_url).text
        response_json = json.loads(response)

        print('lime count:', len(response_json[0]['proxy_list']))

        for proxy in response_json[0]['proxy_list']:
            continue
            prox_str1 = 'https://user-19084:Working1@' + proxy['proxy'] +'/'
            prox_str2 = 'http://user-19084:Working1@' + proxy['proxy'] +'/'
            proxy_dict = {'https':prox_str1, 'http':prox_str2}
            proxy_list.append(proxy_dict)
            p_list.append(proxy_dict)

    except:
        #pass
        traceback.print_exc()

    try:
        gp_resp = requests.get(gp_url).text
        gp_json = json.loads(gp_resp)

        print('ghost count:', len(gp_json['proxies']))

        for proxy in gp_json['proxies']:
            prox_str1 = 'https://102415dan:dan123@' + proxy['ip'] + ':' + proxy['port']
            prox_str2 = 'http://102415dan:dan123@' + proxy['ip'] + ':' + proxy['port']
            proxy_dict = {'https':prox_str1, 'http':prox_str2}
            proxy_list.append(proxy_dict)
            p_list.append(proxy_dict)

    except:
        pass
        #traceback.print_exc()

    print('number of proxies: ', len(proxy_list))

    if len(proxy_list) is 0:
        raise Exception('no working proxies')

    print('number of proxies: ', len(proxy_list))
    return proxy_list

def get_session():
    proxy = random.choice(p_list)
    s = requests.Session()
    s.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:48.0) Gecko/20100101 Firefox/48.0'
    s.proxies = proxy
    print(s.proxies)
    return s

def write_to_file(user, r_text):
    #r_text
    f = open('{0}.html'.format(user), 'w')
    f.write(r_text.encode('ascii', 'ignore'))
    f.close()

def main():
    global p_list
    p_list = getProxylist()
    get_word_weighting()
    create_bots()

    print(len(bots))
    for b in bots:
        b.execute_strategy1('all', 1)
        time.sleep(random.randint(5,30))


main()
