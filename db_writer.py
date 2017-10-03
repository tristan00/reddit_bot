import sqlite3

conn = sqlite3.connect('reddit.db')

c = conn.cursor()
creds = ('dataphobes','SVUhgJCTZrPBeN2U')

c.execute('drop TABLE key_words')
c.execute('CREATE TABLE key_words (word text, value integer)')

for i in creds.keys():
    print([i, creds[i]])
    c.execute('insert into key_words values (?, ?)', [i, creds[i]])
conn.commit()
rs = c.execute('select * from key_words').fetchall()
for r in rs:
    print(r)


