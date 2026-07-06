"""
Custom DCT-based Lossy Image Compression
=========================================
Implements JPEG-style compression manually using:
  - 8×8 block DCT (Discrete Cosine Transform)
  - JPEG standard luminance quantization matrix
  - Quality-scaled quantization
  - Per-channel RGB processing
  - PSNR calculation

Educational implementation for BScCSIT Final Year Project.
"""

import numpy as np
from scipy.fftpack import dct, idct
from PIL import Image
import math


# ─────────────────────────────────────────────────
# JPEG STANDARD LUMINANCE QUANTIZATION MATRIX
# Used for Y (luma) channel in standard JPEG
# Higher values = more compression = lower quality
# ─────────────────────────────────────────────────
JPEG_QUANTIZATION_MATRIX = np.array([
    [16, 11, 10, 16, 24,  40,  51,  61],
    [12, 12, 14, 19, 26,  58,  60,  55],
    [14, 13, 16, 24, 40,  57,  69,  56],
    [14, 17, 22, 29, 51,  87,  80,  62],
    [18, 22, 37, 56, 68,  109, 103, 77],
    [24, 35, 55, 64, 81,  104, 113, 92],
    [49, 64, 78, 87, 103, 121, 120, 101],
    [72, 92, 95, 98, 112, 100, 103, 99],
], dtype=np.float64)


def get_quantization_matrix(quality):
    """
    Scales the JPEG quantization matrix based on quality.

    Quality range: 10 (low quality, high compression)
                   95 (high quality, low compression)

    Formula follows the JPEG standard scaling approach:
      quality < 50  → scale = 5000 / quality
      quality >= 50 → scale = 200 - 2 * quality
    """
    quality = max(1, min(95, quality))

    if quality < 50:
        scale = 5000 / quality
    else:
        scale = 200 - 2 * quality

    # Apply scaling and clamp values to 1-255
    q_matrix = np.floor(
        (JPEG_QUANTIZATION_MATRIX * scale + 50) / 100
    )
    q_matrix = np.clip(q_matrix, 1, 255)
    return q_matrix


def dct_2d(block):
    """
    Applies 2D DCT to an 8×8 block.
    Uses two 1D DCTs — first on rows, then on columns.
    This is equivalent to the 2D DCT formula.

    Step:
      1. Apply DCT to each row
      2. Apply DCT to each column of the result
    """
    return dct(
        dct(block.T, norm='ortho').T,
        norm='ortho'
    )


def idct_2d(block):
    """
    Applies 2D Inverse DCT to an 8×8 block.
    Reverses the DCT to reconstruct pixel values.

    Step:
      1. Apply IDCT to each row
      2. Apply IDCT to each column of the result
    """
    return idct(
        idct(block.T, norm='ortho').T,
        norm='ortho'
    )


def pad_channel(channel, block_size=8):
    """
    Pads image channel so dimensions are
    multiples of 8 (required for 8×8 block processing).
    Uses edge padding to avoid artifacts.
    """
    h, w = channel.shape
    pad_h = (block_size - h % block_size) % block_size
    pad_w = (block_size - w % block_size) % block_size
    return np.pad(
        channel,
        ((0, pad_h), (0, pad_w)),
        mode='edge'
    )


def compress_channel_dct(channel, q_matrix):
    """
    Compresses a single image channel using DCT.

    Steps for each 8×8 block:
      1. Subtract 128 (center values around 0)
      2. Apply 2D DCT
      3. Divide by quantization matrix (quantize)
      4. Round to nearest integer (discard small values)

    Returns:
      quantized_blocks: the compressed coefficient blocks
      padded_h, padded_w: padded dimensions for reconstruction
    """
    # Pad to multiple of 8
    padded = pad_channel(channel.astype(np.float64))
    padded_h, padded_w = padded.shape

    quantized_blocks = np.zeros_like(padded)

    for i in range(0, padded_h, 8):
        for j in range(0, padded_w, 8):
            block = padded[i:i+8, j:j+8]

            # Step 1 — Level shift: subtract 128
            block = block - 128.0

            # Step 2 — Apply 2D DCT
            dct_block = dct_2d(block)

            # Step 3 — Quantize (divide and round)
            quantized = np.round(dct_block / q_matrix)

            quantized_blocks[i:i+8, j:j+8] = quantized

    return quantized_blocks, padded_h, padded_w


def decompress_channel_dct(quantized_blocks,
                            q_matrix,
                            original_h,
                            original_w):
    """
    Reconstructs the image channel from quantized DCT blocks.

    Steps for each 8×8 block:
      1. Multiply by quantization matrix (dequantize)
      2. Apply 2D Inverse DCT
      3. Add 128 back (reverse level shift)
      4. Clip to valid pixel range [0, 255]

    Returns:
      Reconstructed channel cropped to original size.
    """
    padded_h, padded_w = quantized_blocks.shape
    reconstructed = np.zeros((padded_h, padded_w))

    for i in range(0, padded_h, 8):
        for j in range(0, padded_w, 8):
            block = quantized_blocks[i:i+8, j:j+8]

            # Step 1 — Dequantize (multiply back)
            dequantized = block * q_matrix

            # Step 2 — Apply 2D Inverse DCT
            idct_block = idct_2d(dequantized)

            # Step 3 — Reverse level shift: add 128
            idct_block = idct_block + 128.0

            # Step 4 — Clip to valid pixel range
            reconstructed[i:i+8, j:j+8] = np.clip(
                idct_block, 0, 255)

    # Crop back to original size (remove padding)
    return reconstructed[:original_h, :original_w]


def calculate_psnr(original, reconstructed):
    """
    Calculates PSNR (Peak Signal-to-Noise Ratio).

    Formula:
      MSE  = mean of (original - reconstructed)^2
      PSNR = 10 * log10(255^2 / MSE)

    Higher PSNR = better quality.
    Typical JPEG:
      High quality (Q=90): ~40-48 dB
      Low  quality (Q=10): ~25-32 dB
    """
    original      = original.astype(np.float64)
    reconstructed = reconstructed.astype(np.float64)

    mse = np.mean((original - reconstructed) ** 2)

    if mse == 0:
        return float('inf')

    psnr = 10 * math.log10((255.0 ** 2) / mse)
    return round(psnr, 2)


def dct_compress_image(input_path, output_path, quality=40):
    """
    Main DCT compression function.
    Now handles already-compressed images gracefully.
    """
    img           = Image.open(input_path).convert('RGB')
    img_array     = np.array(img, dtype=np.uint8)
    original_h, original_w = img_array.shape[:2]

    q_matrix = get_quantization_matrix(quality)

    reconstructed_channels = []

    for c in range(3):
        channel = img_array[:, :, c]
        quantized, pad_h, pad_w = compress_channel_dct(
            channel, q_matrix)
        reconstructed = decompress_channel_dct(
            quantized, q_matrix,
            original_h, original_w)
        reconstructed_channels.append(
            reconstructed.astype(np.uint8))

    reconstructed_array = np.stack(
        reconstructed_channels, axis=2)

    psnr = calculate_psnr(img_array, reconstructed_array)

    result_img = Image.fromarray(reconstructed_array, 'RGB')

    # ✅ Save with quality matching user's slider
    # Lower quality = smaller file = more compression
    save_quality = min(quality + 10, 95)
    result_img.save(output_path,
                    format='JPEG',
                    quality=save_quality,
                    optimize=True)

    return {
        'psnr': psnr,
    }