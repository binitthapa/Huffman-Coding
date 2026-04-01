import numpy as np
from PIL import Image
from hc_app.huffman import *

def read_image(image_path):
    img = Image.open(image_path).convert('RGB')
    width,height = img.size
    img_array = np.array(img)
    R = img_array[:,:,0].flatten().tolist()
    G = img_array[:,:,1].flatten().tolist()
    B = img_array[:,:,2].flatten().tolist()
    return R,G,B,width,height

def compress_channel(channel):
    freq = build_frequency_table(channel)
    heap = build_priority_queue(freq)
    root = build_huffman_tree(heap)
    codes = generate_codes(root , current_code="", codes={})
    encoded = encode_text(channel, codes)
    return encoded, root

def compress_image(image_path):
    R,G,B,width,height = read_image(image_path)
    print(f"Image size: {width} x {height} pixels")
    print(f"Total pixels: {width * height}")
    print(f"Original bits: {width * height * 3 * 8}")
    print("\n Compressing Red channel..")
    encoded_R , root_R = compress_channel(R)
    print("\n Compressing Green channel..")
    encoded_G , root_G = compress_channel(G)
    print("\nCompressing Blue channel..")
    encoded_B , root_B = compress_channel(B)

    original_bits = width * height * 3 * 8
    compressed_bits = len(encoded_R) + len(encoded_G) + len(encoded_B)
    reduction = round((1-compressed_bits/original_bits)*100,2)
    print(f"\nOriginal bits:{original_bits} bits")
    print(f"Compressed size: {compressed_bits} bits")
    print(f"Size reduction : {reduction} %")

    return{
        "encoded_R" : encoded_R,
        "encoded_G" : encoded_G,
        "encoded_B" : encoded_B,
        "root_R" : root_R,
        "root_G" : root_G,  
        "root_B" : root_B,
        "width" : width,
        "height" : height    }

def decompress_channel(encoded, root):
    decoded = []
    current = root
    for bit in encoded:
        if bit == '0':
            current = current.left
        else:
            current = current.right
        if current.char is not None:
            decoded.append(current.char)
            current = root
    return decoded

def decompress_image(compressed_data , output_path):
    encoded_R = compressed_data["encoded_R"]    
    encoded_G = compressed_data["encoded_G"]
    encoded_B = compressed_data["encoded_B"]
    root_R = compressed_data["root_R"]
    root_G = compressed_data["root_G"]  
    root_B = compressed_data["root_B"]  
    width = compressed_data["width"]
    height = compressed_data["height"]
    print("\n Decompressing Red channel...")
    R = decompress_channel(encoded_R, root_R)
    print("\n Decompressing Green channel...")
    G = decompress_channel(encoded_G, root_G)
    print("\n Decompressing Blue channel...")
    B = decompress_channel(encoded_B, root_B)

    R_2d = np.array(R, dtype= np.uint8).reshape((height, width))
    G_2d = np.array(G, dtype= np.uint8).reshape((height, width))
    B_2d = np.array(B, dtype= np.uint8).reshape((height, width))
    img_array = np.stack([R_2d, G_2d, B_2d], axis=2)
    img = Image.fromarray(img_array , mode='RGB')
    img.save(output_path)
    print(f"\nImage saved to : {output_path}")
    return output_path
