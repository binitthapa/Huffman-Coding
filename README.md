# Huffman Coding Compression Tool

> A full-stack web application for **lossless and lossy file compression** built with Python and Django.  
> Implements custom Huffman Coding and DCT-based image compression from scratch.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Algorithm Details](#algorithm-details)
- [Installation](#installation)
- [Usage](#usage)
- [Supported Formats](#supported-formats)
- [Performance Results](#performance-results)
- [Screenshots](#screenshots)
- [Future Scope](#future-scope)
- [License](#license)

---

## Overview

This project is a **BScCSIT 7th Semester Final Year Project** that demonstrates two compression techniques through a clean web interface:

| Mode | Algorithm | Output | Decompressible |
|---|---|---|---|
| **Lossless** | Custom Huffman Coding | `.huff` binary file |  Yes — 100% exact |
| **Lossy** | Manual DCT (JPEG-style) | Viewable `.jpg` image |  No — irreversible |

The tool handles **multiple file formats** — plain text, documents, source code files, and RGB images — with smart detection that skips re-compression on already-compressed formats such as `.pdf`, `.docx`, and `.zip`.

---

## Features

- **Custom Huffman Implementation** — Node class, frequency table, min-heap priority queue, tree builder, encoder, and decoder all written from scratch
- **Bit Packing** — encoded bit strings are packed into real bytes (8 bits → 1 byte), eliminating the 8× overhead of storing `'0'` and `'1'` as text characters
- **Compact `.huff` Format** — custom binary header stores the extension, serialized tree, and packed data without pickle overhead
- **Smart Skip Mechanism** — detects already-compressed formats and stores raw data with a flag instead of inflating the file size
- **Skip if Larger** — compares compressed vs original size before saving; falls back to raw storage if compression yields no benefit
- **DCT Lossy Compression** — manual 8×8 block DCT on each RGB channel using `scipy.fftpack`, with JPEG-standard quantization matrix scaled by a quality slider (10–95)
- **Lossy Text Compression** — removes extra whitespace, trailing spaces, and blank lines while keeping the file human-readable
- **PSNR Calculation** — computes Peak Signal-to-Noise Ratio for both lossless (`∞ dB`) and lossy (finite dB) results
- **Full Decompression** — upload a `.huff` file to restore the original perfectly; detects image vs file type automatically
- **Bootstrap 5 UI** — responsive interface with drag-and-drop upload, live progress bars, metric cards, image comparison, and download buttons

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.x, Django 6.x |
| **Core Algorithms** | Custom Python (`huffman.py`, `huffman_image.py`, `dct_compress.py`) |
| **Scientific Computing** | NumPy, SciPy (`scipy.fftpack.dct / idct`) |
| **Image Processing** | Pillow (PIL) |
| **Frontend** | HTML5, Bootstrap 5.3, Bootstrap Icons, JavaScript (Fetch API) |
| **Database** | SQLite (Django default) |
| **Version Control** | Git + GitHub |
| **IDE** | Visual Studio Code |

---

## Project Structure

```
huffman/
├── myproject/                  # Django project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── hc_app/                     # Main application
│   ├── huffman.py              # Core Huffman algorithm
│   ├── huffman_image.py        # Image-specific Huffman compression
│   ├── dct_compress.py         # DCT-based lossy compression
│   └── views.py                # Django views + routing logic
│
├── templates/
│   └── index.html              # Single-page Bootstrap UI
│
├── media/
│   ├── uploads/                # User-uploaded original files
│   ├── compressed/             # .huff and lossy output files
│   └── restored/               # Decompressed/restored files
│
├── manage.py
└── requirements.txt
```

---

## Algorithm Details

### Lossless — Huffman Coding

```
Read file as raw bytes (0–255)
        ↓
Build frequency table  (Counter)
        ↓
Build min-heap priority queue
        ↓
Build Huffman Tree  (merge lowest-freq nodes)
        ↓
Generate binary codes  (traverse tree)
        ↓
Encode data → bit string
        ↓
Bit-pack into bytes  (8 bits → 1 byte)
        ↓
Save .huff  [flag | ext | tree | data]
```

**`.huff` file format:**

```
[1 byte]  flag — 0xAB = compressed, 0xCD = raw (skip)
[2 bytes] extension length
[N bytes] original file extension (e.g. "txt")
[4 bytes] serialized tree length
[M bytes] compact binary tree  (leaf: 0x01 + byte, inner: 0x00 + left + right)
[4 bytes] encoded data length
[K bytes] bit-packed encoded data
```

### Lossy — DCT-Based Image Compression

```
Load image → split into R, G, B channels
        ↓
For each channel → divide into 8×8 blocks
        ↓
Subtract 128  (level shift)
        ↓
Apply 2D DCT  (scipy.fftpack — rows then columns)
        ↓
Divide by quantization matrix → round  ← DATA LOSS OCCURS HERE
        ↓
Multiply by quantization matrix  (dequantize)
        ↓
Apply 2D Inverse DCT
        ↓
Add 128 → clip to [0, 255]
        ↓
Reconstruct image from R, G, B channels → save as .jpg
```

**Quantization scaling by quality:**

```python
# quality < 50
scale = 5000 / quality

# quality >= 50
scale = 200 - (2 * quality)

q_matrix = floor((JPEG_MATRIX * scale + 50) / 100)
q_matrix = clip(q_matrix, 1, 255)
```

---

## Installation

### Prerequisites

- Python 3.10 or higher
- pip

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/binitthapa/Huffman-Coding.git
cd Huffman-Coding

# 2. Create and activate virtual environment
python -m venv env

# Windows
env\Scripts\activate

# macOS / Linux
source env/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create media folders
mkdir -p media/uploads media/compressed media/restored

# 5. Run migrations
python manage.py migrate

# 6. Start the development server
python manage.py runserver
```

Open your browser at: **http://127.0.0.1:8000**

### requirements.txt

```
django>=6.0
numpy
pillow
scipy
```

---

## Usage

### Compress a file (Lossless)

1. Select **Lossless** mode
2. Drag and drop or browse for any supported file
3. Click **Compress File**
4. View metrics — original size, compressed size, reduction %, PSNR, execution time
5. Download the **Original**, **Compressed (.huff)**, or **Restored** file

### Compress an image (Lossy DCT)

1. Select **Lossy** mode
2. Upload a `.jpg`, `.png`, `.bmp`, or `.webp` image
3. Adjust the **Quality slider** (10 = high compression, 95 = high quality)
4. Click **Compress (Lossy)**
5. View side-by-side image comparison with PSNR value
6. Download the compressed `.jpg`

### Decompress a `.huff` file

1. Upload a previously generated `.huff` file
2. The tool automatically detects it is a compressed file
3. Click **Decompress File**
4. Download the fully restored original file

---

## Supported Formats

### Lossless Compression (Huffman)

| Category | Extensions |
|---|---|
| **Text / Data** | `.txt`, `.csv`, `.json`, `.xml`, `.yaml`, `.yml`, `.log`, `.md` |
| **Source Code** | `.py`, `.js`, `.ts`, `.css`, `.html`, `.htm`, `.java`, `.c`, `.cpp`, `.h`, `.sql`, `.sh` |
| **Images (lossless)** | `.bmp`, `.png`, `.jpg`, `.jpeg`, `.webp` |
| **Already compressed*** | `.pdf`, `.docx`, `.doc`, `.xlsx`, `.zip`, `.rar`, `.7z`, `.mp3`, `.mp4` |
| **Decompress** | `.huff` |

> *Already-compressed formats are stored raw inside the `.huff` wrapper to prevent size inflation.

### Lossy Compression (DCT)

| Extensions |
|---|
| `.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp` |

---

## Performance Results

### Lossless Compression

| File Type | Original Size | Compressed Size | Ratio | PSNR |
|---|---|---|---|---|
| TXT | 5487.19 KB | 3382.10 KB | 1.6224 | — |
| CSV | 58.39 KB | 28.41 KB | 2.0550 | — |
| PDF | 1254.21 KB | 1263.55 KB | 0.9926 | — |
| PNG | 4340.78 KB | 13916.81 KB | 0.3119 | ∞ dB |

> TXT and CSV compress well due to skewed character distributions.  
> PDF and PNG are already compressed — Huffman adds overhead, stored raw by smart skip.

### Lossy Compression (DCT)

| Image | Format | Original | Compressed | Ratio | PSNR |
|---|---|---|---|---|---|
| Image 1 | JPG | 2271.56 KB | 855.77 KB | 2.6544 | 48.87 dB |
| Image 2 | WEBP | 198.38 KB | 157.43 KB | 1.2601 | 28.10 dB |
| Image 3 | BMP | 1024.00 KB | 24.09 KB | 42.5012 | 32.31 dB |
| Image 4 | PNG | 219.30 KB | 31.86 KB | 6.8828 | 39.11 dB |

> BMP achieves the highest ratio (42.5×) because it is completely uncompressed to begin with.  
> PSNR above 28 dB indicates acceptable to high visual quality in all cases.

### Lossless vs Lossy — Key Comparison

| Metric | Huffman (Lossless) | DCT (Lossy) |
|---|---|---|
| Compression Ratio | 0.31 – 2.06 | 1.26 – 42.50 |
| PSNR | ∞ dB | 28 – 49 dB |
| Reversible |  100% exact |  Irreversible |
| Best for | Text, source code, archival | Photographic images |
| Supports all file types |  Yes |  Images only |

---

## Future Scope

- Implement **LZ77 + Huffman (DEFLATE)** for better compression on binary and already-compressed formats
- Add **YCbCr color space conversion** for true JPEG-standard DCT compression
- Introduce **video compression** using inter-frame motion estimation
- Add **user authentication** with personal compression history and file management
- Support **batch compression** of multiple files simultaneously
- Deploy as a **public cloud service** (AWS / Heroku / Railway)

---

## Author

**Binit Thapa**  
BScCSIT — 7th Semester
Tribhuvan University, Nepal  
GitHub: [@binitthapa](https://github.com/binitthapa)

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

> Built for educational purposes as a Final Year Project demonstrating core data compression algorithms.
