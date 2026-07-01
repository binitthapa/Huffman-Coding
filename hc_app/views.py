import os
import time
from django.shortcuts import render
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from hc_app.huffman import (
    build_frequency_table,
    build_priority_queue,
    build_huffman_tree,
    generate_codes,
    encode_text,
    decode_text,
    pad_encoded_text,
    get_byte_array,
)
from hc_app.huffman_image import (
    compress_image,
    decompress_image,
    get_compression_stats
)


def index(request):
    return render(request, 'index.html')


def download_file(request, file_type, filename):
    folder_map = {
        "original"  : "uploads",
        "restored"  : "restored",
        "compressed": "compressed",
    }

    if file_type not in folder_map:
        raise Http404("Invalid file type")

    file_path = os.path.join(
        settings.MEDIA_ROOT, folder_map[file_type], filename)

    if not os.path.exists(file_path):
        raise Http404("File not found")

    return FileResponse(
        open(file_path, 'rb'),
        as_attachment=True,
        filename=filename
    )


@csrf_exempt
def compress(request):
    if request.method == 'POST' and request.FILES.get('file'):

        uploaded_file = request.FILES['file']
        filename      = uploaded_file.name
        extension     = filename.split('.')[-1].lower()

        upload_path = os.path.join(
            settings.MEDIA_ROOT, 'uploads', filename)
        os.makedirs(
            os.path.dirname(upload_path), exist_ok=True)

        with open(upload_path, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        start_time = time.time()

        image_extensions = [
            'jpg', 'jpeg', 'png', 'bmp', 'tiff', 'webp'
        ]

        try:
            if extension in image_extensions:
                result = handle_image(
                    upload_path, filename, start_time)
            else:
                # ✅ Handles ANY file type — txt, pdf, docx, zip, etc.
                result = handle_any_file(
                    upload_path, filename, start_time)
        except Exception as e:
            return JsonResponse(
                {'error': str(e)}, status=500)

        return JsonResponse(result)

    return JsonResponse(
        {'error': 'No file uploaded'}, status=400)


def handle_image(upload_path, filename, start_time):
    compressed_data = compress_image(upload_path)
    stats = get_compression_stats(
        upload_path, compressed_data)

    base_name          = filename.rsplit('.', 1)[0]
    original_extension = filename.rsplit('.', 1)[1].lower()
    restored_filename  = 'restored_' + base_name + \
                         '.' + original_extension

    restored_path = os.path.join(
        settings.MEDIA_ROOT, 'restored', restored_filename)
    os.makedirs(
        os.path.dirname(restored_path), exist_ok=True)

    decompress_image(compressed_data, restored_path)

    # ✅ NEW — Save the actual compressed .huff file
    huff_filename = base_name + '.huff'
    huff_path     = os.path.join(
        settings.MEDIA_ROOT, 'compressed', huff_filename)
    os.makedirs(
        os.path.dirname(huff_path), exist_ok=True)

    save_image_compressed_file(compressed_data, huff_path)

    exec_time    = round(time.time() - start_time, 2)
    psnr         = stats['overall_psnr']
    psnr_display = '∞ dB' if psnr == float('inf') \
                   else f'{psnr} dB'

    actual_file_size       = os.path.getsize(upload_path)
    actual_compressed_size = os.path.getsize(huff_path)
    actual_reduction       = round(
        (1 - actual_compressed_size / actual_file_size) * 100, 2)
    actual_ratio = round(
        actual_file_size / actual_compressed_size, 4)

    return {
        'success'           : True,
        'file_type'         : 'image',
        'filename'          : filename,
        'original_bits'     : actual_file_size * 8,
        'compressed_bits'   : actual_compressed_size * 8,
        'compression_ratio' : actual_ratio,
        'reduction'         : actual_reduction,
        'psnr'              : psnr_display,
        'execution_time'    : exec_time,
        'original_url'      : f'/download/original/{filename}/',
        'compressed_url'    : f'/download/compressed/{huff_filename}/',
        'restored_url'      : f'/download/restored/{restored_filename}/',
        'width'             : stats['width'],
        'height'            : stats['height'],
    }

def save_image_compressed_file(compressed_data, huff_path):
    """
    Combines R, G, B encoded bit strings into ONE binary file
    using bit packing — so the file is genuinely smaller.
    """
    encoded_R = compressed_data["encoded_R"]
    encoded_G = compressed_data["encoded_G"]
    encoded_B = compressed_data["encoded_B"]

    # Combine all 3 channels into one bit string
    combined_bits = encoded_R + encoded_G + encoded_B

    # Pack bits into actual bytes
    padded   = pad_encoded_text(combined_bits)
    byte_arr = get_byte_array(padded)

    with open(huff_path, 'wb') as f:
        f.write(bytes(byte_arr))


def handle_any_file(upload_path, filename, start_time):
    """
    Works for ANY file type — txt, pdf, docx, zip, exe, etc.
    Reads as BINARY so no data is lost.
    """
    # ✅ Read as binary — works for all file types
    with open(upload_path, 'rb') as f:
        data = f.read()

    if not data:
        return {'error': 'File is empty'}

    byte_list = list(data)   # list of ints 0-255

    freq    = build_frequency_table(byte_list)
    heap    = build_priority_queue(freq)
    root    = build_huffman_tree(heap)
    codes   = generate_codes(root, current_code="", codes={})
    encoded = encode_text(byte_list, codes)
    decoded = decode_text(encoded, root)

    # ✅ Pack bits into real bytes for accurate file size
    padded_encoded = pad_encoded_text(encoded)
    byte_array     = get_byte_array(padded_encoded)

    original_bits = len(data) * 8
    exec_time     = round(time.time() - start_time, 2)
    match         = byte_list == decoded

    # Save compressed .huff file (actual binary, smaller size)
    base_name     = filename.rsplit('.', 1)[0]
    huff_filename = base_name + '.huff'
    huff_path     = os.path.join(
        settings.MEDIA_ROOT, 'compressed', huff_filename)
    os.makedirs(
        os.path.dirname(huff_path), exist_ok=True)
    with open(huff_path, 'wb') as f:
        f.write(bytes(byte_array))

    # Save restored file — exact original bytes, original extension
    restored_filename = 'restored_' + filename
    restored_path     = os.path.join(
        settings.MEDIA_ROOT, 'restored', restored_filename)
    os.makedirs(
        os.path.dirname(restored_path), exist_ok=True)
    with open(restored_path, 'wb') as f:
        f.write(bytes(decoded))

    actual_compressed_bytes = os.path.getsize(huff_path)
    actual_compressed_bits  = actual_compressed_bytes * 8
    actual_reduction        = round(
        (1 - actual_compressed_bytes / len(data)) * 100, 2)
    compression_ratio = round(
        len(data) / actual_compressed_bytes, 4)

    return {
        'success'           : True,
        'file_type'         : 'text',
        'filename'          : filename,
        'original_bits'     : original_bits,
        'compressed_bits'   : actual_compressed_bits,
        'compression_ratio' : compression_ratio,
        'reduction'         : actual_reduction,
        'psnr'              : '∞ dB',
        'execution_time'    : exec_time,
        'lossless'          : match,
        'original_chars'    : len(data),
        'original_url'      : f'/download/original/{filename}/',
        'compressed_url'    : f'/download/compressed/{huff_filename}/',
        'restored_url'      : f'/download/restored/{restored_filename}/',
    }