import os
import re
import time
import pickle
from urllib import request
import numpy as np
from PIL import Image
from django.shortcuts import render
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from hc_app.dct_compress import dct_compress_image

from hc_app.huffman import (
    build_frequency_table,
    build_priority_queue,
    build_huffman_tree,
    generate_codes,
    encode_text,
    decode_text,
    pad_encoded_text,
    get_byte_array,
    remove_padding,
    bytes_to_bitstring,
    save_compressed_file,
    load_compressed_file,
    save_raw_file,  
    is_already_compressed,
    is_huffman_suitable, 
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
        settings.MEDIA_ROOT,
        folder_map[file_type],
        filename)

    if not os.path.exists(file_path):
        raise Http404("File not found")

    
    response = FileResponse(
        open(file_path, 'rb'),
        as_attachment=True,
        filename=filename,
        content_type='application/octet-stream'
    )
    
    response['Content-Disposition'] = \
        f'attachment; filename="{filename}"'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@csrf_exempt
def compress(request):
    if request.method == 'POST' and request.FILES.get('file'):

        uploaded_file = request.FILES['file']
        filename      = uploaded_file.name
        extension     = filename.split('.')[-1].lower()

        mode = request.POST.get('mode', 'lossless')

        upload_path = os.path.join(
            settings.MEDIA_ROOT, 'uploads', filename)
        os.makedirs(
            os.path.dirname(upload_path), exist_ok=True)

        with open(upload_path, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        start_time = time.time()

        image_extensions = [
            'jpg', 'jpeg', 'png',
            'bmp', 'webp'
        ]

        try:
            if extension == 'huff':
                result = handle_huff(
                    upload_path, filename, start_time)

            elif mode == 'lossy':
                if extension in image_extensions:
                    result = handle_lossy_image(upload_path, filename, start_time, request)
                elif extension == 'txt':
                    result = handle_lossy_text(
                        upload_path, filename, start_time)
                else:
                    return JsonResponse({
                        'error':
                        'Lossy compression supports '
                        'images and .txt files only.'
                    }, status=400)

            else:
                if extension in image_extensions:
                    result = handle_image(
                        upload_path, filename, start_time)
                else:
                    result = handle_any_file(
                        upload_path, filename, start_time)

        except Exception as e:
            return JsonResponse(
                {'error': str(e)}, status=500)

        return JsonResponse(result)

    return JsonResponse(
        {'error': 'No file uploaded'}, status=400)


# ── LOSSLESS IMAGE ──
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

    huff_filename = base_name + '.huff'
    huff_path     = os.path.join(
        settings.MEDIA_ROOT, 'compressed', huff_filename)
    os.makedirs(
        os.path.dirname(huff_path), exist_ok=True)
    save_image_huff(compressed_data,
                    huff_path,
                    original_extension)

    exec_time    = round(time.time() - start_time, 2)
    psnr         = stats['overall_psnr']
    psnr_display = '∞ dB' if psnr == float('inf') \
                   else f'{psnr} dB'

    actual_file_size       = os.path.getsize(upload_path)
    actual_compressed_size = os.path.getsize(huff_path)
    actual_reduction       = round(
        (1 - actual_compressed_size /
         actual_file_size) * 100, 2)
    actual_ratio = round(
        actual_file_size / actual_compressed_size, 4)

    return {
        'success'           : True,
        'mode'              : 'lossless',
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


def save_image_huff(compressed_data, huff_path,
                    original_extension):
    encoded_R = compressed_data["encoded_R"]
    encoded_G = compressed_data["encoded_G"]
    encoded_B = compressed_data["encoded_B"]

    bytes_R = bytes(get_byte_array(
        pad_encoded_text(encoded_R)))
    bytes_G = bytes(get_byte_array(
        pad_encoded_text(encoded_G)))
    bytes_B = bytes(get_byte_array(
        pad_encoded_text(encoded_B)))

    package = {
        'type'               : 'image',
        'bytes_R'            : bytes_R,
        'bytes_G'            : bytes_G,
        'bytes_B'            : bytes_B,
        'root_R'             : compressed_data["root_R"],
        'root_G'             : compressed_data["root_G"],
        'root_B'             : compressed_data["root_B"],
        'width'              : compressed_data["width"],
        'height'             : compressed_data["height"],
        'original_extension' : original_extension,
    }

    with open(huff_path, 'wb') as f:
        pickle.dump(package, f)


# ── LOSSLESS ANY FILE ──
def handle_any_file(upload_path, filename, start_time):
    with open(upload_path, 'rb') as f:
        data = f.read()

    if not data:
        return {'error': 'File is empty'}

    extension = filename.rsplit('.', 1)[-1].lower()
    base_name = filename.rsplit('.', 1)[0]
    huff_filename = base_name + '.huff'
    huff_path     = os.path.join(
        settings.MEDIA_ROOT, 'compressed', huff_filename)
    os.makedirs(os.path.dirname(huff_path), exist_ok=True)

    restored_filename = 'restored_' + filename
    restored_path     = os.path.join(
        settings.MEDIA_ROOT, 'restored', restored_filename)
    os.makedirs(os.path.dirname(restored_path), exist_ok=True)

    original_size = len(data)
    compression_skipped = False
    skip_reason = ''

    # Skip compression for already-compressed formats
    if is_already_compressed(extension):
        save_raw_file(data, huff_path, extension)
        with open(restored_path, 'wb') as f:
            f.write(data)
        compression_skipped = True
        skip_reason = (
            f'.{extension} is already compressed internally. '
            'Stored without re-compression.')

    else:
        # Run Huffman
        byte_list = list(data)
        freq      = build_frequency_table(byte_list)
        heap      = build_priority_queue(freq)
        root      = build_huffman_tree(heap)
        codes     = generate_codes(root, current_code="", codes={})
        encoded   = encode_text(byte_list, codes)

        # Try saving compressed first to temp path
        import tempfile
        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix='.huff')
        tmp.close()
        save_compressed_file(encoded, root, tmp.name, extension)
        compressed_size = os.path.getsize(tmp.name)

        if compressed_size >= original_size:
            # Skip — store raw instead
            os.unlink(tmp.name)
            save_raw_file(data, huff_path, extension)
            with open(restored_path, 'wb') as f:
                f.write(data)
            compression_skipped = True
            skip_reason = (
                'Compressed size was larger than original. '
                'Original stored without compression.')
        else:
            # Use compressed file
            import shutil
            shutil.move(tmp.name, huff_path)
            decoded = decode_text(encoded, root)
            with open(restored_path, 'wb') as f:
                f.write(bytes(decoded))

    actual_compressed_bytes = os.path.getsize(huff_path)
    actual_reduction        = round(
        (1 - actual_compressed_bytes / original_size) * 100, 2)
    compression_ratio       = round(
        original_size / actual_compressed_bytes, 4) \
        if actual_compressed_bytes > 0 else 1.0
    exec_time = round(time.time() - start_time, 2)

    return {
        'success'              : True,
        'mode'                 : 'lossless',
        'file_type'            : 'file',
        'filename'             : filename,
        'original_bits'        : original_size * 8,
        'compressed_bits'      : actual_compressed_bytes * 8,
        'compression_ratio'    : compression_ratio,
        'reduction'            : actual_reduction,
        'psnr'                 : '∞ dB',
        'execution_time'       : exec_time,
        'lossless'             : True,
        'original_chars'       : original_size,
        'compression_skipped'  : compression_skipped,
        'skip_reason'          : skip_reason,
        'original_url'         : f'/download/original/{filename}/',
        'compressed_url'       : f'/download/compressed/{huff_filename}/',
        'restored_url'         : f'/download/restored/{restored_filename}/',
    }

# ── LOSSY IMAGE — Custom DCT Implementation ──
def handle_lossy_image(upload_path, filename,
                       start_time, request):
    quality   = int(request.POST.get('quality', 40))
    quality   = max(10, min(95, quality))
    base_name = filename.rsplit('.', 1)[0]
    extension = filename.rsplit('.', 1)[1].lower()

    compressed_filename = 'lossy_dct_' + base_name + '.jpg'
    compressed_path     = os.path.join(
        settings.MEDIA_ROOT, 'compressed', compressed_filename)
    os.makedirs(
        os.path.dirname(compressed_path), exist_ok=True)

    try:
        result = dct_compress_image(
            input_path  = upload_path,
            output_path = compressed_path,
            quality     = quality
        )

        psnr      = result['psnr']
        exec_time = round(time.time() - start_time, 2)

        original_size   = os.path.getsize(upload_path)
        compressed_size = os.path.getsize(compressed_path)

        reduction = round(
            (1 - compressed_size / original_size) * 100, 2)
        ratio     = round(
            original_size / compressed_size, 4) \
            if compressed_size > 0 else 1.0

        size_increased = compressed_size > original_size

        if psnr == float('inf'):
            psnr_display = '∞ dB'
        else:
            psnr_display = f'{psnr} dB'

        return {
            'success'           : True,
            'mode'              : 'lossy',
            'file_type'         : 'lossy_image',
            'filename'          : filename,
            'original_bits'     : original_size * 8,
            'compressed_bits'   : compressed_size * 8,
            'compression_ratio' : ratio,
            'reduction'         : reduction,
            'psnr'              : psnr_display,
            'execution_time'    : exec_time,
            'quality'           : quality,
            'lossless'          : False,
            'size_increased'    : size_increased, 
            'original_url'      : f'/download/original/{filename}/',
            'compressed_url'    : f'/download/compressed/{compressed_filename}/',
        }

    except Exception as e:
        return {'error': f'DCT compression failed: {str(e)}'}

# ── LOSSY TEXT ──
def handle_lossy_text(upload_path, filename, start_time):
    with open(upload_path, 'r',
              encoding='utf-8', errors='ignore') as f:
        original_text = f.read()

    if not original_text:
        return {'error': 'File is empty'}

    compressed_text = original_text
    compressed_text = '\n'.join(
        line.rstrip()
        for line in compressed_text.splitlines()
    )
    compressed_text = compressed_text.replace('\t', ' ')
    compressed_text = re.sub(r' {2,}', ' ', compressed_text)
    compressed_text = re.sub(r'\n{3,}', '\n\n', compressed_text)
    compressed_text = compressed_text.strip()

    original_size   = len(original_text.encode('utf-8'))
    compressed_size = len(compressed_text.encode('utf-8'))
    reduction       = round(
        (1 - compressed_size / original_size) * 100, 2)
    ratio           = round(
        original_size / compressed_size, 4) \
        if compressed_size > 0 else 1.0
    exec_time       = round(time.time() - start_time, 2)

    base_name           = filename.rsplit('.', 1)[0]
    compressed_filename = 'lossy_' + filename
    compressed_path     = os.path.join(
        settings.MEDIA_ROOT, 'compressed', compressed_filename)
    os.makedirs(
        os.path.dirname(compressed_path), exist_ok=True)

    with open(compressed_path, 'w', encoding='utf-8') as f:
        f.write(compressed_text)

    return {
        'success'           : True,
        'mode'              : 'lossy',
        'file_type'         : 'lossy_text',
        'filename'          : filename,
        'original_bits'     : original_size * 8,
        'compressed_bits'   : compressed_size * 8,
        'compression_ratio' : ratio,
        'reduction'         : reduction,
        'psnr'              : 'N/A',
        'execution_time'    : exec_time,
        'original_chars'    : len(original_text),
        'compressed_chars'  : len(compressed_text),
        'lossless'          : False,
        'original_url'      : f'/download/original/{filename}/',
        'compressed_url'    : f'/download/compressed/{compressed_filename}/',
    }


# ── DECOMPRESS .huff ──
def handle_huff(upload_path, filename, start_time):

    # Detect file format from first byte
    with open(upload_path, "rb") as f:
        first_byte = f.read(1)

    base_name = filename.rsplit('.', 1)[0]
    exec_time = round(time.time() - start_time, 2)

    # New Huffman binary format
    if first_byte in (b'\xAB', b'\xCD'):
        return handle_huff_text(
            base_name,
            filename,
            upload_path,
            exec_time
        )

    # Old pickle format (images)
    try:
        with open(upload_path, "rb") as f:
            package = pickle.load(f)

        if package.get("type") == "image":
            return handle_huff_image(
                package,
                base_name,
                filename,
                upload_path,
                exec_time
            )

        return handle_huff_text(
            base_name,
            filename,
            upload_path,
            exec_time
        )

    except Exception as e:
        return {
            "error": f"Invalid or corrupted .huff file. ({str(e)})"
        }


def handle_huff_image(package, base_name,
                      filename, upload_path, exec_time):
    root_R             = package['root_R']
    root_G             = package['root_G']
    root_B             = package['root_B']
    width              = package['width']
    height             = package['height']
    original_extension = package.get(
        'original_extension', 'png')

    bit_R = remove_padding(
        bytes_to_bitstring(package['bytes_R']))
    bit_G = remove_padding(
        bytes_to_bitstring(package['bytes_G']))
    bit_B = remove_padding(
        bytes_to_bitstring(package['bytes_B']))

    R = decode_text(bit_R, root_R)
    G = decode_text(bit_G, root_G)
    B = decode_text(bit_B, root_B)

    R_2d = np.array(R, dtype=np.uint8).reshape(height, width)
    G_2d = np.array(G, dtype=np.uint8).reshape(height, width)
    B_2d = np.array(B, dtype=np.uint8).reshape(height, width)

    img_array = np.stack([R_2d, G_2d, B_2d], axis=2)
    img       = Image.fromarray(img_array, mode='RGB')

    format_map = {
        'jpg' : 'JPEG', 'jpeg': 'JPEG',
        'png' : 'PNG',  'bmp' : 'BMP',
        'webp': 'WEBP', 'tiff': 'TIFF',
    }
    save_format = format_map.get(original_extension, 'PNG')

    restored_filename = 'decompressed_' + \
                        base_name + '.' + original_extension
    restored_path     = os.path.join(
        settings.MEDIA_ROOT, 'restored', restored_filename)
    os.makedirs(
        os.path.dirname(restored_path), exist_ok=True)
    img.save(restored_path, format=save_format)

    huff_size     = os.path.getsize(upload_path)
    restored_size = os.path.getsize(restored_path)

    return {
        'success'           : True,
        'file_type'         : 'decompress',
        'filename'          : filename,
        'original_bits'     : huff_size * 8,
        'compressed_bits'   : restored_size * 8,
        'compression_ratio' : round(restored_size / huff_size, 4),
        'reduction'         : 0,
        'psnr'              : '∞ dB',
        'execution_time'    : exec_time,
        'lossless'          : True,
        'restored_url'      : f'/download/restored/{restored_filename}/',
        'original_url'      : f'/download/original/{filename}/',
    }


def handle_huff_text(base_name,
                     filename,
                     upload_path,
                     exec_time):
    # load_compressed_file now returns 4 values
    encoded, root, original_extension, raw_bytes = \
        load_compressed_file(upload_path)

    restored_filename = 'decompressed_' + \
                        base_name + '.' + original_extension
    restored_path     = os.path.join(
        settings.MEDIA_ROOT, 'restored', restored_filename)
    os.makedirs(
        os.path.dirname(restored_path), exist_ok=True)

    if raw_bytes is not None:
        # Was stored raw — restore directly
        with open(restored_path, 'wb') as f:
            f.write(raw_bytes)
    else:
        decoded = decode_text(encoded, root)
        with open(restored_path, 'wb') as f:
            f.write(bytes(decoded))

    huff_size     = os.path.getsize(upload_path)
    restored_size = os.path.getsize(restored_path)

    return {
        'success'           : True,
        'file_type'         : 'decompress',
        'filename'          : filename,
        'original_bits'     : huff_size * 8,
        'compressed_bits'   : restored_size * 8,
        'compression_ratio' : round(restored_size / huff_size, 4),
        'reduction'         : 0,
        'psnr'              : '∞ dB',
        'execution_time'    : exec_time,
        'lossless'          : True,
        'restored_url'      : f'/download/restored/{restored_filename}/',
        'original_url'      : f'/download/original/{filename}/',
    }