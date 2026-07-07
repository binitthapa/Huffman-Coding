import heapq
import struct
import pickle
from collections import Counter


ALREADY_COMPRESSED = {
    'pdf', 'docx', 'doc', 'xlsx', 'xls', 'pptx', 'ppt',
    'zip', 'rar', '7z', 'gz', 'tar', 'bz2', 'xz',
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp',
    'mp3', 'mp4', 'avi', 'mkv', 'mov', 'aac', 'ogg',
    'apk', 'exe', 'dll',
}

HUFFMAN_SUITABLE = {
    'txt', 'csv', 'json', 'xml', 'html', 'htm',
    'py', 'js', 'css', 'java', 'c', 'cpp', 'h',
    'ts', 'md', 'log', 'yaml', 'yml', 'ini', 'cfg',
    'sql', 'sh', 'bat', 'r', 'swift', 'go', 'rs',
}


def is_already_compressed(extension):
    return extension.lower() in ALREADY_COMPRESSED


def is_huffman_suitable(extension):
    return extension.lower() in HUFFMAN_SUITABLE


class Node:
    def __init__(self, char=None, freq=None):
        self.char  = char
        self.freq  = freq
        self.left  = None
        self.right = None

    def __lt__(self, other):
        return self.freq < other.freq


def build_frequency_table(data):
    return Counter(data)


def build_priority_queue(frequency_table):
    heap = []
    for symbol, freq in frequency_table.items():
        node = Node(symbol, freq)
        heapq.heappush(heap, node)
    return heap


def build_huffman_tree(heap):
    if len(heap) == 1:
        only_node = heapq.heappop(heap)
        wrapper   = Node(freq=only_node.freq)
        wrapper.left = only_node
        return wrapper

    while len(heap) > 1:
        left  = heapq.heappop(heap)
        right = heapq.heappop(heap)
        merged       = Node(freq=left.freq + right.freq)
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
        codes[node.char] = current_code if current_code else "0"
        return codes
    generate_codes(node.left,  current_code + "0", codes)
    generate_codes(node.right, current_code + "1", codes)
    return codes


def encode_text(data, codes):
    return "".join(codes[symbol] for symbol in data)


def decode_text(encoded, root):
    decoded = []
    current = root

    if current.char is not None:
        return [current.char] * (len(encoded) if encoded else 0)

    for bit in encoded:
        current = current.left if bit == "0" else current.right
        if current.char is not None:
            decoded.append(current.char)
            current = root

    return decoded


# ── Bit packing ──

def pad_encoded_text(encoded_text):
    extra_padding = 8 - (len(encoded_text) % 8)
    if extra_padding == 8:
        extra_padding = 0
    encoded_text += "0" * extra_padding
    padded_info   = "{0:08b}".format(extra_padding)
    return padded_info + encoded_text


def get_byte_array(padded_encoded_text):
    if len(padded_encoded_text) % 8 != 0:
        raise ValueError("Encoded text not padded properly")
    b = bytearray()
    for i in range(0, len(padded_encoded_text), 8):
        b.append(int(padded_encoded_text[i:i+8], 2))
    return b


def remove_padding(bit_string):
    extra_padding = int(bit_string[:8], 2)
    bit_string    = bit_string[8:]
    if extra_padding > 0:
        bit_string = bit_string[:-extra_padding]
    return bit_string


def bytes_to_bitstring(byte_data):
    return "".join("{0:08b}".format(b) for b in byte_data)


# ── Compact tree serialization ──

def serialize_tree(node):
    """
    Compact binary tree format:
      Leaf  → b'1' + 1 byte (symbol 0-255)
      Inner → b'0' + left + right
    Much smaller than pickle overhead.
    """
    if node is None:
        return b''
    if node.char is not None:
        return b'\x01' + bytes([node.char])
    return b'\x00' + serialize_tree(node.left) + \
                     serialize_tree(node.right)


def deserialize_tree(data, index=0):
    if index >= len(data):
        return None, index
    flag = data[index]
    index += 1
    if flag == 1:  # leaf
        char = data[index]
        index += 1
        return Node(char=char, freq=0), index
    # inner node
    left,  index = deserialize_tree(data, index)
    right, index = deserialize_tree(data, index)
    inner        = Node(freq=0)
    inner.left   = left
    inner.right  = right
    return inner, index


# ── File I/O ──

# Flag bytes written at start of .huff file
_FLAG_COMPRESSED = b'\xAB'   # Huffman compressed
_FLAG_RAW        = b'\xCD'   # stored raw (compression skipped)


def save_compressed_file(encoded, root, output_path,
                          original_extension="bin"):
    """
    Format:
      [1 byte flag] [2 bytes ext_len] [ext bytes]
      [4 bytes tree_len] [tree bytes]
      [4 bytes data_len] [packed bit data]
    """
    padded   = pad_encoded_text(encoded)
    data_bytes = bytes(get_byte_array(padded))
    tree_bytes = serialize_tree(root)
    ext_bytes  = original_extension.encode('utf-8')

    with open(output_path, 'wb') as f:
        f.write(_FLAG_COMPRESSED)
        f.write(struct.pack('>H', len(ext_bytes)))
        f.write(ext_bytes)
        f.write(struct.pack('>I', len(tree_bytes)))
        f.write(tree_bytes)
        f.write(struct.pack('>I', len(data_bytes)))
        f.write(data_bytes)


def save_raw_file(original_data, output_path,
                  original_extension="bin"):
    """
    Skip compression — store original bytes with flag.
    Decompressor detects flag and restores directly.
    """
    ext_bytes = original_extension.encode('utf-8')
    with open(output_path, 'wb') as f:
        f.write(_FLAG_RAW)
        f.write(struct.pack('>H', len(ext_bytes)))
        f.write(ext_bytes)
        f.write(original_data)


def load_compressed_file(huff_path):
    """
    Returns (encoded_bitstring | None, root | None,
             original_extension, raw_bytes | None)
    raw_bytes is set only when flag = RAW.
    """
    with open(huff_path, 'rb') as f:
        flag = f.read(1)

        ext_len = struct.unpack('>H', f.read(2))[0]
        original_extension = f.read(ext_len).decode('utf-8')

        if flag == _FLAG_RAW:
            raw_bytes = f.read()
            return None, None, original_extension, raw_bytes

        # Compressed
        tree_len   = struct.unpack('>I', f.read(4))[0]
        tree_bytes = f.read(tree_len)
        root, _    = deserialize_tree(bytearray(tree_bytes))

        data_len   = struct.unpack('>I', f.read(4))[0]
        data_bytes = f.read(data_len)

        bit_string = bytes_to_bitstring(data_bytes)
        encoded    = remove_padding(bit_string)

        return encoded, root, original_extension, None