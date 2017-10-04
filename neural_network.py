

class neural_network():
    def __init__(self):
        self.parent_nodes = {}
        self.child_nodes = {}

    def feed_list(self, word_list):
        if word_list[0] not in self.parent_nodes:
            self.parent_nodes.append(word_list[0])
            self.child_nodes.append(word_list[0])
        


class node():
    def __init__(self, content):
        self.content = content
        self.edges_to = []
        self.edges_from = []
