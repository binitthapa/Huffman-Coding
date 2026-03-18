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
    
def build_frequency_table(text):
    return Counter(text)    
    
def build_priority_queue(frequency_table):
    heap = []
    for symbol, freq in frequency_table.items():
        node =Node (symbol, freq)
        heapq.heappush(heap, node)
    return heap
    
def build_huffman_tree(heap):
    while len(heap) > 1 :
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        merged = Node(freq = left.freq + right.freq)
        merged.left = left
        merged.right = right
        heapq.heappush(heap, merged)
    return heap[0]
    
def generate_codes(node, current_code = "", codes = {}):
    if node is None:
        return 
    if node.char is not None:
        codes[node.char] = current_code
        return
    generate_codes(node.left, current_code + "0", codes)
    generate_codes(node.right, current_code + "1", codes)
    return codes
    
def encode_text(text, codes):
    encoded = ""
    for char in text:
        encoded += codes[char]
    return encoded
        
