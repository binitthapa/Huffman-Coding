let selectedFile     = null;
let progressInterval = null;
let rVal = 0, gVal = 0, bVal = 0;

const IMAGE_EXTENSIONS = [
    'jpg','jpeg','png','bmp','webp'
];

// ── Mode selector ──
function getMode() {
    return document.querySelector(
        'input[name="compressionMode"]:checked').value;
}

function getQuality() {
    return parseInt(
        document.getElementById('qualitySlider').value);
}

function updateMode() {
    let mode = getMode();

    if (mode === 'lossless') {
        document.getElementById('badgesLossless')
                .classList.remove('d-none');
        document.getElementById('badgesLossy')
                .classList.add('d-none');
        document.getElementById('qualitySliderRow')
                .classList.add('d-none');
    } else {
        document.getElementById('badgesLossless')
                .classList.add('d-none');
        document.getElementById('badgesLossy')
                .classList.remove('d-none');
        document.getElementById('qualitySliderRow')
                .classList.remove('d-none');
    }

    let ext = selectedFile ?
              selectedFile.name.split('.').pop().toLowerCase()
              : '';
    if (selectedFile && ext !== 'huff') {
        document.getElementById('compressBtn').innerHTML =
            mode === 'lossy' ?
            'Compress ' :
            'Compress';
    }
}

function handleDragOver(e) {
    e.preventDefault();
    document.getElementById('dropZone')
            .classList.add('bg-primary', 'bg-opacity-10');
}

function handleDragLeave() {
    document.getElementById('dropZone')
            .classList.remove('bg-primary', 'bg-opacity-10');
}

function handleDrop(e) {
    e.preventDefault();
    document.getElementById('dropZone')
            .classList.remove('bg-primary', 'bg-opacity-10');
    if (e.dataTransfer.files.length > 0) {
        setFile(e.dataTransfer.files[0]);
    }
}

// ── File Selection ──
function handleFileSelect(e) {
    if (e.target.files[0]) setFile(e.target.files[0]);
}

function setFile(file) {
    selectedFile = file;
    document.getElementById('selectedFileName')
            .textContent = file.name +
            ' (' + formatBytes(file.size) + ')';
    document.getElementById('fileSelected')
            .classList.remove('d-none');
    document.getElementById('compressBtn').disabled = false;

    let ext  = file.name.split('.').pop().toLowerCase();
    let mode = getMode();

    if (ext === 'huff') {
        if (mode === 'lossy') {
            showError(
                'Lossy mode does not support .huff files. ' +
                'Switch to Lossless mode to decompress.');
            document.getElementById('compressBtn').disabled = true;
            return;
        }
        document.getElementById('compressBtn').innerHTML =
            '<i class="bi bi-arrow-counterclockwise me-2"></i>' +
            'Decompress';
        document.getElementById('statusMsg').textContent =
            '.huff file ready — click Decompress!';
    } else {
        updateMode();
        document.getElementById('statusMsg').textContent =
            'Click Compress !';
    }
}

function formatBytes(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576)
        return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / 1048576).toFixed(2) + ' MB';
}

// ── Start Compression ──
function startCompression() {
    if (!selectedFile) return;

    let ext  = selectedFile.name.split('.').pop().toLowerCase();
    let mode = getMode();

    if (mode === 'lossy' && ext === 'huff') {
        showError(
            'Lossy mode does not support .huff files. ' +
            'Switch to Lossless mode to decompress.');
        return;
    }

    if (mode === 'lossy') {
        if (!IMAGE_EXTENSIONS.includes(ext) && ext !== 'txt') {
            showError(
                'Lossy compression supports images ' +
                '(.jpg .png .bmp .webp) ' +
                'and .txt files only.');
            return;
        }
    }

    document.getElementById('compressBtn').disabled = true;
    document.getElementById('statusMsg').innerHTML =
        '<span class="spinner-border spinner-border-sm me-2"></span>' +
        'Processing... please wait';

   ['progressSection','imageSection','infoNote'].forEach(id => {
    let el = document.getElementById(id);
    el.classList.add('d-none');
    el.style.display = '';
});

    if (
    mode === 'lossless' &&
    IMAGE_EXTENSIONS.includes(ext) &&
    ext !== 'huff'
) {
    document.getElementById('progressSection')
            .classList.remove('d-none');

    startProgress();
}

    let formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('mode', mode);
    formData.append('quality', getQuality());

    fetch('/compress/', {
    method: 'POST',
    body: formData
})
.then(r => r.json())
.then(data => {

    console.log(data);   // ← ADD THIS LINE

    if (data.success) {
        showResults(data);
    } else {
        showError(data.error || 'Unknown error');
    }
})
.catch(err => showError(err.toString()));
}

function startProgress() {
    rVal = 0; gVal = 0; bVal = 0;
    progressInterval = setInterval(() => {
        if (rVal < 90) rVal += 3;
        if (gVal < 85) gVal += 2;
        if (bVal < 88) bVal += 2.5;
        updateBar('rBar', 'rPct', rVal);
        updateBar('gBar', 'gPct', gVal);
        updateBar('bBar', 'bPct', bVal);
    }, 150);
}

function updateBar(barId, pctId, val) {
    val = Math.min(Math.round(val), 100);
    document.getElementById(barId).style.width  = val + '%';
    document.getElementById(pctId).textContent  = val + '%';
}

function showResults(data) {
    clearInterval(progressInterval);

    if (data.file_type === 'image') {
    updateBar('rBar', 'rPct', 100);
    updateBar('gBar', 'gPct', 100);
    updateBar('bBar', 'bPct', 100);
}

    // ── DECOMPRESS ──
    if (data.file_type === 'decompress') {
        show('extraStatsSection');
        document.getElementById('compRatio')
                .textContent = data.compression_ratio + 'x';
        document.getElementById('execTime')
                .textContent = data.execution_time + 's';
        document.getElementById('lossless').innerHTML =
            '<span class="text-success">Yes</span>';

        let dlSection =
            document.getElementById('downloadSection');
        dlSection.classList.remove('d-none');
        dlSection.style.display = 'flex';

        document.getElementById('downloadOriginal')
                .style.display = 'none';
        document.getElementById('downloadCompressed')
                .style.display = 'none';
        document.getElementById('downloadRestored')
                .style.display = 'inline-block';
        document.getElementById('downloadRestored')
                .href = data.restored_url;
        document.getElementById('downloadRestored')
                .innerHTML =
                '<i class="bi bi-download me-2"></i>' +
                'Download Decompressed File';

        showInfoNote(
            'Decompression complete! ' +
            'Your original file has been perfectly recovered.');

        document.getElementById('statusMsg').innerHTML =
            '<span class="text-success fw-bold">' +
            'Decompression complete!</span>';
        document.getElementById('compressBtn').disabled = false;
        return;
    }

    // ── METRICS ──
    let origKB = (data.original_bits / 8 / 1024)
                 .toFixed(2) + ' KB';
    let compKB = (data.compressed_bits / 8 / 1024)
                 .toFixed(2) + ' KB';

    show('metricsSection');
    document.getElementById('origSize').textContent  = origKB;
    document.getElementById('compSize').textContent  = compKB;
    document.getElementById('reduction').textContent =
        data.reduction + '%';
    document.getElementById('psnr').textContent = data.psnr;

    show('extraStatsSection');
    document.getElementById('compRatio').textContent =
        data.compression_ratio + 'x';
    document.getElementById('execTime').textContent  =
        data.execution_time + 's';
    document.getElementById('lossless').innerHTML =
        data.lossless !== false ?
        '<span class="text-success">Yes</span>' :
        '<span class="text-warning">No (Lossy)</span>';

    let dlSection =
        document.getElementById('downloadSection');
    dlSection.classList.remove('d-none');
    dlSection.style.display = 'flex';

    // ── LOSSLESS IMAGE ──
    if (data.file_type === 'image') {
        show('imageSection');
        document.getElementById('originalImg')
                .src = data.original_url;
        document.getElementById('compressedImg')
                .src = data.restored_url;
        document.getElementById('compImgBadge')
                .textContent = 'Identical';
        document.getElementById('compImgBadge')
                .className = 'badge bg-success rounded-pill';

        setDownloads(
            data.original_url,
            data.compressed_url,
            data.restored_url,
            'Download Original',
            'Download Compressed (.huff)',
            'Download Restored'
        );

        showInfoNote(
            'Lossless compression complete! ' +
            'The .huff file contains Huffman-encoded data. ' +
            'Upload it back to decompress and recover ' +
            'the original image perfectly.');
    }

    // ── LOSSLESS TEXT ──
    else if (data.file_type === 'text') {
        

        setDownloads(
            data.original_url,
            data.compressed_url,
            data.restored_url,
            'Download Original',
            'Download Compressed (.huff)',
            'Download Restored'
        );

        showInfoNote(
            'Lossless compression complete! ' +
            'Upload the .huff file back to decompress ' +
            'and recover your original file perfectly.');
    }
    // ── LOSSLESS DOCUMENTS (DOCX, PDF, etc.) ──
else if (data.file_type === 'file') {
    setDownloads(
        data.original_url,
        data.compressed_url,
        data.restored_url,
        'Download Original',
        'Download Compressed (.huff)',
        'Download Restored'
    );

    showInfoNote(
        'Lossless compression complete! ' +
        'Upload the .huff file back to decompress ' +
        'and recover your original file perfectly.');
}

    // ── LOSSY IMAGE ──
    else if (data.file_type === 'lossy_image') {
        show('imageSection');
        document.getElementById('originalImg')
                .src = data.original_url;
        document.getElementById('compressedImg')
                .src = data.compressed_url;
        document.getElementById('compImgBadge')
                .textContent = 'Viewable .jpg (Q=' +
                               data.quality + ')';
        document.getElementById('compImgBadge')
                .className =
                'badge bg-warning text-dark rounded-pill';

        
       

        setDownloads(
            data.original_url,
            data.compressed_url,
            null,
            'Download Original',
            'Download Compressed (.jpg)',
            null
        );

        showInfoNote(
            'Lossy compression complete! ' +
            'Compressed .jpg is directly viewable. ' +
            'Quality=' + data.quality + ' — ' +
            data.reduction + '% size reduction. ' +
            'Lossy files cannot be decompressed back.');
    }

    // ── LOSSY TEXT ──
    else if (data.file_type === 'lossy_text') {
    

        setDownloads(
            data.original_url,
            data.compressed_url,
            null,
            'Download Original',
            'Download Compressed (.txt)',
            null
        );

        showInfoNote(
            'Lossy text compression complete! ' +
            'Extra spaces and blank lines removed. ' +
            'Original: ' + data.original_chars +
            ' chars → Compressed: ' +
            data.compressed_chars +
            ' chars. Output is fully readable.');
    }

    document.getElementById('statusMsg').innerHTML =
        '<span class="text-success fw-bold">' +
        'Compression complete!</span>';
    document.getElementById('compressBtn').disabled = false;
}

// ── Helpers ──
function setDownloads(origUrl, compUrl, restUrl,
                      origLabel, compLabel, restLabel) {
    let origBtn = document.getElementById('downloadOriginal');
    let compBtn = document.getElementById('downloadCompressed');
    let restBtn = document.getElementById('downloadRestored');

    if (origUrl) {
        origBtn.href = origUrl;
        origBtn.innerHTML =
            '<i class="bi bi-download me-2"></i>' + origLabel;
        origBtn.style.display = 'inline-block';
    } else {
        origBtn.style.display = 'none';
    }

    if (compUrl) {
        compBtn.href = compUrl;
        compBtn.innerHTML =
            '<i class="bi bi-download me-2"></i>' + compLabel;
        compBtn.style.display = 'inline-block';
    } else {
        compBtn.style.display = 'none';
    }

    if (restUrl) {
        restBtn.href = restUrl;
        restBtn.innerHTML =
            '<i class="bi bi-download me-2"></i>' + restLabel;
        restBtn.style.display = 'inline-block';
    } else {
        restBtn.style.display = 'none';
    }
}

function showInfoNote(text) {
    let el = document.getElementById('infoNote');
    el.classList.remove('d-none');
    document.getElementById('infoNoteText').textContent = text;
}

function show(id) {
    document.getElementById(id).classList.remove('d-none');
}

function showError(msg) {
    clearInterval(progressInterval);
    document.getElementById('statusMsg').innerHTML =
        '<span class="text-danger">❌ ' + msg + '</span>';
    document.getElementById('compressBtn').disabled = false;
}

// ── Reset ──
function resetAll() {
    selectedFile = null;
    clearInterval(progressInterval);

    ['progressSection','metricsSection',
     'extraStatsSection','imageSection',
     'compareSection','fileSelected','infoNote']
    .forEach(id => {
        document.getElementById(id).classList.add('d-none');
    });

    let dlSection = document.getElementById('downloadSection');
    dlSection.classList.add('d-none');
    dlSection.style.display = '';

    ['rBar','gBar','bBar','hBar'].forEach(id => {
        document.getElementById(id).style.width = '0%';
    });
    ['rPct','gPct','bPct','hPct'].forEach(id => {
        document.getElementById(id).textContent = '0%';
    });

    document.getElementById('compressBtn').disabled  = true;
    document.getElementById('compressBtn').innerHTML =
        'Compress';
    document.getElementById('statusMsg').textContent =
        'Select a file to get started';
    document.getElementById('fileInput').value = '';
    document.getElementById('dropZone')
            .classList.remove('bg-primary', 'bg-opacity-10');

    updateMode();
}