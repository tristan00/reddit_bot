from nltk.tokenize import sent_tokenize, word_tokenize
import tensorflow as tf
import sqlite3
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import random
import pickle
from collections import Counter
import numpy as np

hm_lines = 100000

stop = set(stopwords.words('english'))
stop.update(['.', ',', '"', "'", '?', '!', ':', ';', '(', ')', '[', ']', '{', '}'])

upvote_list1 = []
upvote_list2 = []
subs = {}


def word_count(str):
    return len(word_tokenize(str.lower()))

def sentence_count(str):
    return len(sent_tokenize(str.lower()))

def get_percentile(num, parent):
    if parent:
        upvote_list = upvote_list1
    else:
        upvote_list = upvote_list2
    upvote_list.sort()
    for i in upvote_list:
        if i >= num:
            return (upvote_list.index(i) + 1)/len(upvote_list)
    return 0

def upvote_classification(upvotes, parent):
    rank = get_percentile(upvotes, parent)
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

def sub_classification(sub):
    array = [0 for i in range(len(subs.keys()))]
    for i in subs.keys():
        if i == sub:
            array[subs[i]] = 1
            break
    return array

def get_data():
    global upvote_list1
    global upvote_list2
    global subs
    conn = sqlite3.connect('reddit.db')
    subs = {}
    for count, i in enumerate(list(conn.execute('select distinct subreddit from posts ').fetchall())):
        subs[i[0]] = count
    inputs = list(conn.execute('select c1.text, c1.upvotes, c2.text, c2.upvotes, p.subreddit, p.title from comment c1 join comment c2 on c1.comment_id = c2.parent_id  join posts p on c1.post_id = p.post_id where c1.upvotes is not null and c2.upvotes is not null').fetchall())

    print("num of comments: ", len(inputs))
    full_text_parent = ""
    full_text_child = ""
    full_text_title = ""

    for i in inputs:
        upvote_list1.append(i[1])
        upvote_list2.append(i[3])
        temp_child = i[0]
        temp_parent = i[2]
        for j in stop:
            temp_child.replace(j, '')
            temp_parent.replace(j, '')
        full_text_parent += (temp_parent + ' ')
        full_text_child += (temp_child + ' ')

    fdist_parent = nltk.FreqDist(word_tokenize(full_text_parent))
    fdist_child = nltk.FreqDist(word_tokenize(full_text_child))
    fdist_title = nltk.FreqDist(word_tokenize(full_text_child))
    return fdist_parent, fdist_child, inputs

def create_features(n, fdist_parent, fdist_child, inputs):
    parent_most_common_words = list(fdist_parent.most_common(n))
    child_most_common_words = list(fdist_child.most_common(n))

    feature_set = []
    # upvote buckets parent, subreddit,  then child words, then parent words, ~115 length
    for i in inputs:
        temp_array = []
        temp_array.extend(upvote_classification(i[1], True))
        temp_array.extend(sub_classification(i[4]))

        for j in list(child_most_common_words):
            if j[0] in i[2]:
                temp_array.append(1)
            else:
                temp_array.append(0)

        for j in parent_most_common_words:
            if j[0] in i[2]:
                temp_array.append(1)
            else:
                temp_array.append(0)
        temp_features = temp_array
        if upvote_classification(i[3], False) is not None:
            temp_features= [temp_features, upvote_classification(i[3], False)]
            feature_set.append(temp_features)
            #print(temp_features)
    return feature_set

def create_feature_sets_and_labels(n, fdist_parent, fdist_child, inputs):
    test_size = .1
    lexicon = create_features(n, fdist_parent, fdist_child, inputs)
    random.shuffle(lexicon)
    features = np.array(lexicon)

    testing_size = int(test_size*len(features))
    train_x = list(features[:,0][:-testing_size])
    train_y = list(features[:,1][:-testing_size])
    test_x = list(features[:,0][testing_size:])
    test_y = list(features[:,1][testing_size:])

    return train_x, train_y, test_x, test_y

def neural_network_model(train_x, train_y, test_x, test_y, nodes_per_layer, layers):
    if layers ==3:
        #TODO: figure out how to pull reddit data
        n_nodes_hl1 = nodes_per_layer
        n_nodes_hl2 = nodes_per_layer
        n_nodes_hl3 = nodes_per_layer
        n_classes = 5

        #TODO: figure out modify for reddit data
        x = tf.placeholder('float', [None, len(train_x[0])])
        y = tf.placeholder('float')
        hidden_1_layer = {'weights': tf.Variable(tf.random_normal([len(train_x[0]), n_nodes_hl1])),
                          'biases': tf.Variable(tf.random_normal([n_nodes_hl1]))}
        hidden_2_layer = {'weights': tf.Variable(tf.random_normal([n_nodes_hl1, n_nodes_hl2])),
                          'biases': tf.Variable(tf.random_normal([n_nodes_hl2]))}
        hidden_3_layer = {'weights': tf.Variable(tf.random_normal([n_nodes_hl2, n_nodes_hl3])),
                          'biases': tf.Variable(tf.random_normal([n_nodes_hl3]))}
        output_layer = {'weights': tf.Variable(tf.random_normal([n_nodes_hl3, n_classes])),
                      'biases': tf.Variable(tf.random_normal([n_classes]))}

        l1 = tf.add(tf.matmul(x, hidden_1_layer['weights']), hidden_1_layer['biases'])
        l1 = tf.nn.relu(l1)

        l2 = tf.add(tf.matmul(l1, hidden_2_layer['weights']), hidden_2_layer['biases'])
        l2 = tf.nn.relu(l2)

        l3 = tf.add(tf.matmul(l2, hidden_3_layer['weights']), hidden_3_layer['biases'])
        l3 = tf.nn.relu(l3)

        output = tf.add(tf.matmul(l3, output_layer['weights']),  output_layer['biases'])
        return output, x, y
    elif layers == 4:
        #TODO: figure out how to pull reddit data
        n_nodes_hl1 = nodes_per_layer
        n_nodes_hl2 = nodes_per_layer
        n_nodes_hl3 = nodes_per_layer
        n_nodes_hl4 = nodes_per_layer
        n_classes = 5

        #TODO: figure out modify for reddit data
        x = tf.placeholder('float', [None, len(train_x[0])])
        y = tf.placeholder('float')
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

        l1 = tf.add(tf.matmul(x, hidden_1_layer['weights']), hidden_1_layer['biases'])
        l1 = tf.nn.relu(l1)

        l2 = tf.add(tf.matmul(l1, hidden_2_layer['weights']), hidden_2_layer['biases'])
        l2 = tf.nn.relu(l2)

        l3 = tf.add(tf.matmul(l2, hidden_3_layer['weights']), hidden_3_layer['biases'])
        l3 = tf.nn.relu(l3)

        l4 = tf.add(tf.matmul(l3, hidden_4_layer['weights']), hidden_4_layer['biases'])
        l4 = tf.nn.relu(l4)

        output = tf.add(tf.matmul(l4, output_layer['weights']),  output_layer['biases'])
        return output, x, y

    elif layers == 5:
        n_nodes_hl1 = nodes_per_layer
        n_nodes_hl2 = nodes_per_layer
        n_nodes_hl3 = nodes_per_layer
        n_nodes_hl4 = nodes_per_layer
        n_nodes_hl5 = nodes_per_layer
        n_classes = 5

        #TODO: figure out modify for reddit data
        x = tf.placeholder('float', [None, len(train_x[0])])
        y = tf.placeholder('float')
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

        l1 = tf.add(tf.matmul(x, hidden_1_layer['weights']), hidden_1_layer['biases'])
        l1 = tf.nn.relu(l1)

        l2 = tf.add(tf.matmul(l1, hidden_2_layer['weights']), hidden_2_layer['biases'])
        l2 = tf.nn.relu(l2)

        l3 = tf.add(tf.matmul(l2, hidden_3_layer['weights']), hidden_3_layer['biases'])
        l3 = tf.nn.relu(l3)

        l4 = tf.add(tf.matmul(l3, hidden_4_layer['weights']), hidden_4_layer['biases'])
        l4 = tf.nn.relu(l4)

        l5 = tf.add(tf.matmul(l4, hidden_5_layer['weights']), hidden_5_layer['biases'])
        l5 = tf.nn.relu(l5)

        output = tf.add(tf.matmul(l5, output_layer['weights']),  output_layer['biases'])
        return output, x, y


def train_neural_network(data, train_x, train_y, test_x, test_y, nodes_per_layer, layers):
    prediction, x, y = neural_network_model(train_x, train_y, test_x, test_y, nodes_per_layer, layers)
    cost = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=prediction, labels=y))
    optimizer = tf.train.AdamOptimizer().minimize(cost)
    batch_size = 100
    print(1)

    hm_epochs = 20
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

                _, c = sess.run([optimizer, cost], feed_dict= {x:batch_x, y:batch_y})
                epoch_loss += c
                i += batch_size
            print("Epoch", epoch, 'completed out of', hm_epochs, 'loss:', epoch_loss)

        correct = tf.equal(tf.argmax(prediction, 1), tf.argmax(y, 1))
        accuracy = tf.reduce_mean(tf.cast(correct, 'float'))
        accuracy_float = accuracy.eval({x:test_x, y:test_y})
        print('Accuracy:', accuracy_float)
        return accuracy_float



def run_nn(word_list_size, fdist_parent, fdist_child, inputs, nodes_per_layer, layers):
    train_x, train_y, test_x, test_y = create_feature_sets_and_labels(word_list_size, fdist_parent, fdist_child, inputs)
    print('Features created: ')
    data = tf.placeholder('float')
    return train_neural_network(data, train_x, train_y, test_x, test_y, nodes_per_layer, layers)


def run_testing():
    fdist_parent, fdist_child, inputs = get_data()
    results = []
    for layers in range(3,6):
        for nodes in range(500,2500,250):
            for words in range(40,200,20):
                print()
                print()
                print('New test:')
                print('num of layers:', layers, ', nodes per layer:', nodes, ', input words:', words)
                accuracy = run_nn(words, fdist_parent, fdist_child, inputs, nodes, layers)
                results.append({'layers': layers, 'nodes_per_layer': nodes, 'words': words, 'accuracy:': accuracy})
                print()
                print('current_results:')
                for i in results:
                    print(i)

def predict_bucket(parent_text, subreddit, post_title):
    pass

run_testing()



