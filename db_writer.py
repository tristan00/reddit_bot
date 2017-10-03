import sqlite3

conn = sqlite3.connect('reddit.db')

c = conn.cursor()
cred_list = []
creds = ('dataphobes','SVUhgJCTZrPBeN2U')
cred_list.append(creds)

c.execute('drop TABLE reddit_logins')
c.execute('CREATE TABLE reddit_logins (user_name text, password integer)')

for i in cred_list:
    c.execute('insert into reddit_logins values (?, ?)', [i[0], i[1]])
conn.commit()



