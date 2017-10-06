import statistics
import re

class response_word_graph():
    def __init__(self):
        self.parent_nodes = {}
        self.child_nodes = {}

    def add_item(self, parent_word, child_word, value):
        if child_word not in self.child_nodes.keys() or parent_word not in self.child_nodes[child_word].edges.keys():
            self.child_nodes[child_word]= node(child_word)
            self.child_nodes[child_word].edges[parent_word] = [value]
        else:
            self.child_nodes[child_word].edges[parent_word].append(value)

    def values_statement(self, parent_words, child_words):

        child_words_value = []
        for w in child_words:
            temp_value = []
            for w2 in parent_words:
                try:
                    temp_value.append(self.child_nodes[w].get_edge_median(w2))
                except:
                    #key error
                    temp_value.append(0)
            child_words_value.append(statistics.mean(temp_value))

        return sum(child_words_value)/max(len(child_words),len(parent_words))

class node():
    def __init__(self, content):
        self.max_length = -100
        self.min_length = 2
        self.content = content.lower()
        self.edges = {}
        self.average = 0
        self.median = 0

    def get_edge_value(self, in_word):
        if in_word in self.edges.keys():
            return self.edges[in_word]
        return 0

    def get_edge_median(self, in_word):
        if in_word in self.edges.keys() and len(self.edges[in_word])>self.min_length:
            return statistics.median(self.edges[in_word])
        return 0

    def get_edge_mean(self, in_word):
        if in_word in self.edges.keys() and len(self.edges[in_word])>self.min_length:
            return statistics.mean(self.edges[in_word])
        return 0



