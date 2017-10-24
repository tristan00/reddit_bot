#TODO: add model saving

from nltk.tokenize import sent_tokenize, word_tokenize
import tensorflow as tf
import sqlite3
import nltk
from nltk.corpus import stopwords
import random
import pickle
import numpy as np
import time
hm_lines = 1000000
stop = set(stopwords.words('english'))
stop.update(['.', ',', '"', "'", '?', '!', ':', ';', '(', ')', '[', ']', '{', '}', r"\n"])
n_classes = 5

class comment_model():
    def __init__(self):
        self.sess = None
        self.upvote_list1 = []
        self.upvote_list2 = []
        self.subs = {}
        self.fdist_parent = None
        self.fdist_child = None
        self.fdist_title = None
        self.parent_most_common_words = None
        self.child_most_common_words = None
        self.title_most_common_words = None
        self.prediction = None
        self.inputs = None
        self.x = None
        self.block_size = 0
        self.save_path = None

    def get_bucket(self, subreddit, child, parent, title):
        cleaned_input = self.process_input_into_features([parent,None,child, None, subreddit, title])
        batch_x = np.array(cleaned_input)
        print(self.block_size)
        #batch_x = np.reshape(batch_x, (1, self.block_size))
        predictions = self.prediction.eval(session = self.sess, feed_dict = {self.x:batch_x})
        print('predictions:')
        print(predictions)

    def train_neural_network(self, word_list_size, nodes_per_layer, layers, refresh):
        start_time = time.time()
        print('Reading data:', time.time() -start_time)
        if self.inputs is None or refresh:
            self.inputs = self.get_data(word_list_size)
        train_x, train_y, test_x, test_y = self.create_feature_sets_and_labels(.1, self.inputs)

        #data = tf.placeholder('float')
        print('Building network:', time.time() -start_time)
        self.x = tf.placeholder('float', [None, len(train_x[0])])
        self.y = tf.placeholder('float', [None, n_classes])
        self.prediction = self.neural_network_model(train_x, train_y, test_x, test_y, nodes_per_layer, layers)
        cost = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=self.prediction, labels=self.y))
        print('Building optimizer:', time.time() -start_time)
        optimizer = tf.train.AdamOptimizer().minimize(cost)
        batch_size = 100
        hm_epochs = 20
        print('Running session:', time.time() -start_time)

        with tf.Session() as sess:
            sess.run(tf.global_variables_initializer())
            for epoch in range(hm_epochs):
                epoch_loss = 0
                i=0
                while i < len(train_x):
                    start = i
                    end = i + batch_size
                    batch_x = np.array(train_x[start:end])
                    batch_y = np.array(train_y[start:end])
                    _, c = sess.run([optimizer, cost], feed_dict= {self.x:batch_x, self.y:batch_y})
                    epoch_loss += c
                    i += batch_size
                print("Epoch", epoch, 'completed out of', hm_epochs, 'loss:', epoch_loss)
            correct = tf.equal(tf.argmax(self.prediction, 1), tf.argmax(self.y, 1))
            accuracy = tf.reduce_mean(tf.cast(correct, 'float'))
            accuracy_float = accuracy.eval(feed_dict = {self.x:test_x, self.y:test_y})
            print('Finished learning, time taken:', time.time() - start_time)
            print({'layers': layers, 'nodes_per_layer': nodes_per_layer, 'words': word_list_size, 'accuracy:': accuracy_float})
            print('Accuracy:', accuracy_float)

            subreddit = 'dota2'
            child = 'No Flashing his rubick tits would definitely have been flashier'
            parent = "Him sitting there afk would be just as as hitting someone out of vendetta and blinking out"
            title = 'NaVi vs Secret Post Match Discussion'

            cleaned_input = self.process_input_into_features([parent,None,child, None, subreddit, title, '100', '100', '100'])
            batch_x = np.array(cleaned_input)
            #batch_x = np.reshape(batch_x, (1, self.block_size))
            batch_x = np.transpose(batch_x)
            print('Batch:', batch_x)
            predictions = sess.run(self.prediction, feed_dict = {self.x:[batch_x]})
            print('Predictions:', predictions)
            print('here')

    def process_input_into_features(self, input_item):
        temp_array = []
        temp_array.extend(self.sub_classification(input_item[4]))
        temp_array.extend(self.time_classification(input_item[6], input_item[7]))
        temp_array.extend(self.time_classification(input_item[6], input_item[8]))

        for j in self.child_most_common_words:
            if j[0] in input_item[0]:
                temp_array.append(1)
            else:
                temp_array.append(0)

        for j in self.parent_most_common_words:
            if j[0] in input_item[2]:
                temp_array.append(1)
            else:
                temp_array.append(0)
        for j in self.title_most_common_words:
            if j[0] in input_item[5]:
                temp_array.append(1)
            else:
                temp_array.append(0)
        self.block_size = len(temp_array)
        return temp_array


    def create_features(self,inputs):
        feature_set = []
        # upvote buckets parent, subreddit,  then child words, then parent words, ~115 length

        for i in inputs:
            temp = self.process_input_into_features(i)
            if self.upvote_classification(i[3], False) is not None:
                temp_features= [temp, self.upvote_classification(i[3], False)]
                feature_set.append(temp_features)
        return feature_set

    def create_feature_sets_and_labels(self, test_size,  inputs):
        random.shuffle(inputs)
        lexicon = self.create_features(inputs)
        features = np.array(lexicon)

        testing_size = int(test_size*len(features))
        train_x = list(features[:,0][:-testing_size])
        train_y = list(features[:,1][:-testing_size])
        test_x = list(features[:,0][testing_size:])
        test_y = list(features[:,1][testing_size:])

        return train_x, train_y, test_x, test_y

    def get_data(self, n):
        conn = sqlite3.connect('reddit.db')
        self.subs = {}
        for count, i in enumerate(list(conn.execute('select distinct subreddit from posts ').fetchall())):
            self.subs[i[0]] = count
        inputs = list(conn.execute('select c1.text, c1.upvotes, c2.text, c2.upvotes, p.subreddit, p.post_title, p.timestamp, c1.timestamp, c2.timestamp '
                                   'from comment c1 join comment c2 on c1.comment_id = c2.parent_id  join posts p on c1.post_id = p.post_id '
                                   'where c1.upvotes is not null and c2.upvotes is not null').fetchall())

        print("num of comments: ", len(inputs))
        full_text_parent = ""
        full_text_child = ""
        full_text_title = ""

        for i in inputs:
            self.upvote_list1.append(i[1])
            self.upvote_list2.append(i[3])
            temp_child = i[0]
            temp_parent = i[2]
            temp_title = i[5]
            for j in list(stop):
                temp_child.replace(j, '')
                temp_parent.replace(j, '')
                temp_title.replace(j, '')
            full_text_parent += (temp_parent + ' ')
            full_text_child += (temp_child + ' ')
            full_text_title += (temp_title + ' ')

        temp_child =[word for word in word_tokenize(full_text_child.lower()) if word not in stop]
        temp_parent =[word for word in word_tokenize(full_text_parent.lower()) if word not in stop]
        temp_title =[word for word in word_tokenize(full_text_title.lower()) if word not in stop]

        self.fdist_parent = nltk.FreqDist(temp_parent)
        self.fdist_child = nltk.FreqDist(temp_child)
        self.fdist_title = nltk.FreqDist(temp_title)

        self.parent_most_common_words = list(self.fdist_parent.most_common(n))
        self.child_most_common_words = list(self.fdist_child.most_common(n))
        self.title_most_common_words = list(self.fdist_title.most_common(n))
        return inputs

    def neural_network_model(self, train_x, train_y, test_x, test_y, nodes_per_layer, layers):
        n_nodes_hl1 = nodes_per_layer
        n_nodes_hl2 = nodes_per_layer
        n_nodes_hl3 = nodes_per_layer
        n_nodes_hl4 = nodes_per_layer
        n_nodes_hl5 = nodes_per_layer
        n_classes = 5


        if layers == 0:
            output_layer = {'weights': tf.Variable(tf.random_normal([len(train_x[0]), n_classes])),
              'biases': tf.Variable(tf.random_normal([n_classes]))}

            output = tf.matmul(self.x, output_layer['weights']) +  output_layer['biases']
            return output

        if layers == 1:
            hidden_1_layer = {'weights': tf.Variable(tf.random_normal([len(train_x[0]), n_nodes_hl1])),
                  'biases': tf.Variable(tf.random_normal([n_nodes_hl1]))}
            output_layer = {'weights': tf.Variable(tf.random_normal([n_nodes_hl1, n_classes])),
              'biases': tf.Variable(tf.random_normal([n_classes]))}

            l1 = tf.add(tf.matmul(self.x, hidden_1_layer['weights']), hidden_1_layer['biases'])
            l1 = tf.nn.relu(l1)
            output = tf.matmul(l1, output_layer['weights']) +   output_layer['biases']
            return output

        if layers == 2:
            hidden_1_layer = {'weights': tf.Variable(tf.random_normal([len(train_x[0]), n_nodes_hl1])),
                  'biases': tf.Variable(tf.random_normal([n_nodes_hl1]))}
            hidden_2_layer = {'weights': tf.Variable(tf.random_normal([n_nodes_hl1, n_nodes_hl2])),
                              'biases': tf.Variable(tf.random_normal([n_nodes_hl2]))}
            output_layer = {'weights': tf.Variable(tf.random_normal([n_nodes_hl2, n_classes])),
              'biases': tf.Variable(tf.random_normal([n_classes]))}

            l1 = tf.add(tf.matmul(self.x, hidden_1_layer['weights']), hidden_1_layer['biases'])
            l1 = tf.nn.relu(l1)
            l2 = tf.add(tf.matmul(l1, hidden_2_layer['weights']), hidden_2_layer['biases'])
            l2 = tf.nn.relu(l2)
            output = tf.matmul(l2, output_layer['weights'])+  output_layer['biases']
            return output

        if layers ==3:
            hidden_1_layer = {'weights': tf.Variable(tf.random_normal([len(train_x[0]), n_nodes_hl1])),
                              'biases': tf.Variable(tf.random_normal([n_nodes_hl1]))}
            hidden_2_layer = {'weights': tf.Variable(tf.random_normal([n_nodes_hl1, n_nodes_hl2])),
                              'biases': tf.Variable(tf.random_normal([n_nodes_hl2]))}
            hidden_3_layer = {'weights': tf.Variable(tf.random_normal([n_nodes_hl2, n_nodes_hl3])),
                              'biases': tf.Variable(tf.random_normal([n_nodes_hl3]))}
            output_layer = {'weights': tf.Variable(tf.random_normal([n_nodes_hl3, n_classes])),
                          'biases': tf.Variable(tf.random_normal([n_classes]))}

            l1 = tf.add(tf.matmul(self.x, hidden_1_layer['weights']), hidden_1_layer['biases'])
            l1 = tf.nn.relu(l1)
            l2 = tf.add(tf.matmul(l1, hidden_2_layer['weights']), hidden_2_layer['biases'])
            l2 = tf.nn.relu(l2)
            l3 = tf.add(tf.matmul(l2, hidden_3_layer['weights']), hidden_3_layer['biases'])
            l3 = tf.nn.relu(l3)
            output = tf.matmul(l3, output_layer['weights'])+  output_layer['biases']
            return output

        elif layers == 4:
            hidden_1_layer = {'weights': tf.Variable(tf.random_normal([len(train_x[0]), n_nodes_hl1])),
                              'biases': tf.Variable(tf.random_normal([n_nodes_hl1]))}
            hidden_2_layer = {'weights': tf.Variable(tf.random_normal([n_nodes_hl1, n_nodes_hl2])),
                              'biases': tf.Variable(tf.random_normal([n_nodes_hl2]))}
            hidden_3_layer = {'weights': tf.Variable(tf.random_normal([n_nodes_hl2, n_nodes_hl3])),
                              'biases': tf.Variable(tf.random_normal([n_nodes_hl3]))}
            hidden_4_layer = {'weights': tf.Variable(tf.random_normal([n_nodes_hl3, n_nodes_hl4])),
                              'biases': tf.Variable(tf.random_normal([n_nodes_hl4]))}
            output_layer = {'weights': tf.Variable(tf.random_normal([n_nodes_hl4, n_classes])),
                          'biases': tf.Variable(tf.random_normal([n_classes]))}

            l1 = tf.add(tf.matmul(self.x, hidden_1_layer['weights']), hidden_1_layer['biases'])
            l1 = tf.nn.relu(l1)
            l2 = tf.add(tf.matmul(l1, hidden_2_layer['weights']), hidden_2_layer['biases'])
            l2 = tf.nn.relu(l2)
            l3 = tf.add(tf.matmul(l2, hidden_3_layer['weights']), hidden_3_layer['biases'])
            l3 = tf.nn.relu(l3)
            l4 = tf.add(tf.matmul(l3, hidden_4_layer['weights']), hidden_4_layer['biases'])
            l4 = tf.nn.relu(l4)
            output = tf.matmul(l4, output_layer['weights'])+  output_layer['biases']
            return output

        elif layers == 5:
            hidden_1_layer = {'weights': tf.Variable(tf.random_normal([len(train_x[0]), n_nodes_hl1])),
                              'biases': tf.Variable(tf.random_normal([n_nodes_hl1]))}
            hidden_2_layer = {'weights': tf.Variable(tf.random_normal([n_nodes_hl1, n_nodes_hl2])),
                              'biases': tf.Variable(tf.random_normal([n_nodes_hl2]))}
            hidden_3_layer = {'weights': tf.Variable(tf.random_normal([n_nodes_hl2, n_nodes_hl3])),
                              'biases': tf.Variable(tf.random_normal([n_nodes_hl3]))}
            hidden_4_layer = {'weights': tf.Variable(tf.random_normal([n_nodes_hl3, n_nodes_hl4])),
                              'biases': tf.Variable(tf.random_normal([n_nodes_hl4]))}
            hidden_5_layer = {'weights': tf.Variable(tf.random_normal([n_nodes_hl4, n_nodes_hl5])),
                              'biases': tf.Variable(tf.random_normal([n_nodes_hl5]))}
            output_layer = {'weights': tf.Variable(tf.random_normal([n_nodes_hl5, n_classes])),
                                'biases': tf.Variable(tf.random_normal([n_classes]))}

            l1 = tf.add(tf.matmul(self.x, hidden_1_layer['weights']), hidden_1_layer['biases'])
            l1 = tf.nn.relu(l1)
            l2 = tf.add(tf.matmul(l1, hidden_2_layer['weights']), hidden_2_layer['biases'])
            l2 = tf.nn.relu(l2)
            l3 = tf.add(tf.matmul(l2, hidden_3_layer['weights']), hidden_3_layer['biases'])
            l3 = tf.nn.relu(l3)
            l4 = tf.add(tf.matmul(l3, hidden_4_layer['weights']), hidden_4_layer['biases'])
            l4 = tf.nn.relu(l4)
            l5 = tf.add(tf.matmul(l4, hidden_5_layer['weights']), hidden_5_layer['biases'])
            l5 = tf.nn.relu(l5)
            output = tf.matmul(l5, output_layer['weights']) +   output_layer['biases']
            return output

    def get_percentile(self, num, parent):
        if parent:
            upvote_list = self.upvote_list1
        else:
            upvote_list = self.upvote_list2
        upvote_list.sort()
        for i in upvote_list:
            if i >= num:
                return (upvote_list.index(i) + 1)/len(upvote_list)
        return 0

    def upvote_classification(self, upvotes, parent):
        rank = self.get_percentile(upvotes, parent)
        if rank < .2:
            return [1, 0, 0, 0, 0]
        if rank < .4:
            return [0, 1, 0, 0, 0]
        if rank < .6:
            return [0, 0, 1, 0, 0]
        if rank < .8:
            return [0, 0, 0, 1, 0]
        else:
            return [0, 0, 0, 0, 1]

    def time_classification(self, post_time, comment_time):
        time_list = [0 for i in range(24)]
        try:
            time_list[int((float(comment_time) - float(post_time[:10]))/3600)] = 1
            return time_list
        except:
            return time_list

    def sub_classification(self, sub):
        array = [0 for i in range(len(self.subs.keys()))]
        for i in self.subs.keys():
            if i == sub:
                array[self.subs[i]] = 1
                break
        return array

def word_count(str):
    return len(word_tokenize(str.lower()))

def sentence_count(str):
    return len(sent_tokenize(str.lower()))

test_struct = comment_model()
test_struct.train_neural_network(200, 2000, 5, False)
