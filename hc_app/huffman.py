import heapq
from collections import Counter
class Node:
    def __init__(self, char=None, freq=None):
        self.char = char
        self.freq = freq
        self.left = None
        self.right = None
    
    def __lt__(self, other):
        return self.freq < other.freq

    def built_frequency_table(text):
        return Counter(text)    
    
    def priority_queue(frequency_table):
        heapq = []
        for symbol, freq in frequency_table.items():
            node =Node (symbol, freq)
            heapq.heappush(heapq, node)
        return heapq