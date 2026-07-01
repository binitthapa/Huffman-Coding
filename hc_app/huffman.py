import heapq
from collections import Counter


class Node:
    def __init__(self, char=None, freq=None):
        self.char  = char
        self.freq  = freq
        self.left  = None
        self.right = None

    def __lt__(self, other):
        return self.freq < other.freq


def build_frequency_table(data):
    """Works on list of characters OR list of bytes (ints)"""
    return Counter(data)


def build_priority_queue(frequency_table):
    heap = []
    for symbol, freq in frequency_table.items():
        node = Node(symbol, freq)
        heapq.heappush(heap, node)
    return heap


def build_huffman_tree(heap):
    # Edge case — only one unique symbol in file
    if len(heap) == 1:
        only_node = heapq.heappop(heap)
        wrapper = Node(freq=only_node.freq)
        wrapper.left = only_node
        return wrapper

    while len(heap) > 1:
        left  = heapq.heappop(heap)
        right = heapq.heappop(heap)
        merged = Node(freq=left.freq + right.freq)
        merged.left  = left
        merged.right = right
        heapq.heappush(heap, merged)

    return heap[0]


def generate_codes(node, current_code="", codes=None):
    if codes is None:
        codes = {}

    if node is None:
        return codes

    if node.char is not None:
        # Edge case — single symbol gets code "0"
        codes[node.char] = current_code if current_code else "0"
        return codes

    generate_codes(node.left, current_code + "0", codes)
    generate_codes(node.right, current_code + "1", codes)
    return codes


def encode_text(data, codes):
    """data = list of chars or bytes, codes = dict"""
    encoded = "".join(codes[symbol] for symbol in data)
    return encoded


def decode_text(encoded, root):
    """Returns a LIST of symbols (chars or byte ints)"""
    decoded = []
    current = root

    # Edge case — tree has only one node (single symbol file)
    if current.char is not None:
        return [current.char] * (len(encoded) if encoded else 0)

    for bit in encoded:
        if bit == "0":
            current = current.left
        else:
            current = current.right

        if current.char is not None:
            decoded.append(current.char)
            current = root

    return decoded


# ─────────────────────────────────────
# BIT PACKING — converts bit-string to actual bytes
# ─────────────────────────────────────

def pad_encoded_text(encoded_text):
    """
    Pads bit string to multiple of 8.
    Stores padding amount in first 8 bits.
    """
    extra_padding = 8 - (len(encoded_text) % 8)
    if extra_padding == 8:
        extra_padding = 0

    encoded_text += "0" * extra_padding

    padded_info  = "{0:08b}".format(extra_padding)
    encoded_text = padded_info + encoded_text

    return encoded_text


def get_byte_array(padded_encoded_text):
    """Converts padded bit string into real bytes"""
    if len(padded_encoded_text) % 8 != 0:
        raise ValueError("Encoded text not padded properly")

    b = bytearray()
    for i in range(0, len(padded_encoded_text), 8):
        byte = padded_encoded_text[i:i + 8]
        b.append(int(byte, 2))

    return b


def remove_padding(bit_string):
    """Removes the padding when decompressing"""
    padded_info   = bit_string[:8]
    extra_padding = int(padded_info, 2)

    bit_string = bit_string[8:]
    if extra_padding > 0:
        bit_string = bit_string[:-extra_padding]

    return bit_string


def bytes_to_bitstring(byte_data):
    """Converts raw bytes back into a bit string"""
    bit_string = ""
    for byte in byte_data:
        bit_string += "{0:08b}".format(byte)
    return bit_string