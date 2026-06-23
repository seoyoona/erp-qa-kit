"""Screen-label extraction from spec screenshots (v0.3 vision dimension).

The 화면설계서 xlsx embeds a screenshot of the screen layout whose visible Korean
field labels (입고년월, 품목명 …) exist nowhere in the cell text — only in the image.
This module reads those labels for FREE and on-device using the macOS **Vision**
framework (no API, no cost, good Korean accuracy), via a tiny Swift helper compiled
on first use. On any non-macOS host (or without the Swift toolchain) OCR degrades
gracefully to empty output and the caller reports the dimension as unavailable
rather than failing.

Embedded images that are EMF/WMF (vector metafiles openpyxl drops and that we have
no offline converter for) are manifested as skipped, not OCR'd.
"""
from __future__ import annotations

import hashlib
import platform
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

# Raster formats we can hand to the OCR engine directly. EMF/WMF need a converter
# we do not ship, so they are listed as skipped instead.
_RASTER_EXTS = {".png", ".jpg", ".jpeg"}
_VECTOR_EXTS = {".emf", ".wmf"}

_OCR_ENGINE = "macos-vision"

# Swift helper: Apple Vision text recognition, Korean + English, accurate level.
_HELPER_SWIFT = r"""
import Foundation
import Vision
import AppKit

guard CommandLine.arguments.count > 1 else { exit(2) }
guard let img = NSImage(contentsOfFile: CommandLine.arguments[1]),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { exit(3) }
let req = VNRecognizeTextRequest { (request, _) in
    guard let obs = request.results as? [VNRecognizedTextObservation] else { return }
    for o in obs { if let t = o.topCandidates(1).first { print(t.string) } }
}
req.recognitionLevel = .accurate
req.usesLanguageCorrection = true
req.recognitionLanguages = ["ko-KR", "en-US"]
try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
"""

_HANGUL_RE = re.compile(r"[가-힣]")


def _helper_path() -> Path | None:
    """Compile (once, cached by source hash) and return the Vision OCR helper, or
    None if this host cannot build/run it (non-macOS or no swiftc)."""
    if platform.system() != "Darwin":
        return None
    swiftc = shutil.which("swiftc")
    if not swiftc:
        return None
    digest = hashlib.sha1(_HELPER_SWIFT.encode("utf-8")).hexdigest()[:12]
    bin_path = Path(tempfile.gettempdir()) / f"erpqa_ocr_vision_{digest}"
    if bin_path.exists():
        return bin_path
    src = bin_path.with_suffix(".swift")
    src.write_text(_HELPER_SWIFT, encoding="utf-8")
    proc = subprocess.run(
        [swiftc, "-O", str(src), "-o", str(bin_path)],
        capture_output=True, text=True,
    )
    return bin_path if proc.returncode == 0 and bin_path.exists() else None


def ocr_available() -> bool:
    return _helper_path() is not None


def ocr_image(png_path: Path) -> list[str]:
    """Recognized text lines from an image, or [] if OCR is unavailable/failed."""
    helper = _helper_path()
    if helper is None:
        return []
    try:
        proc = subprocess.run(
            [str(helper), str(png_path)], capture_output=True, text=True, timeout=120
        )
    except (subprocess.SubprocessError, OSError):
        return []
    if proc.returncode != 0:
        return []
    return [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]


def extract_spec_images(xlsx_path: Path, out_dir: Path) -> tuple[list[Path], list[str]]:
    """Unzip the spec's embedded media. Returns (raster_image_paths, skipped_notes)
    where skipped_notes describes EMF/WMF metafiles we cannot OCR offline."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rasters: list[Path] = []
    skipped: list[str] = []
    with zipfile.ZipFile(xlsx_path) as zf:
        media = [n for n in zf.namelist() if n.startswith("xl/media/")]
        for name in sorted(media):
            ext = Path(name).suffix.lower()
            if ext in _RASTER_EXTS:
                dest = out_dir / Path(name).name
                dest.write_bytes(zf.read(name))
                rasters.append(dest)
            elif ext in _VECTOR_EXTS:
                skipped.append(f"{Path(name).name} ({ext[1:].upper()} metafile, no offline converter)")
    return rasters, skipped


def is_label(text: str) -> bool:
    """Keep visible field labels (short Korean captions); drop grid data, codes,
    and numbers that the OCR also returns. Heuristic — labels are short and mostly
    Hangul, e.g. 입고년월 / 품목코드 / 거래처."""
    s = text.strip()
    if not (2 <= len(s) <= 12):
        return False
    hangul = _HANGUL_RE.findall(s)
    if len(hangul) < 2:
        return False
    # Reject obvious DATA the OCR also returns: digits (codes/amounts), parenthesised
    # values, and company markers ((주)…) — field labels in these specs carry none.
    if re.search(r"\d", s) or "(" in s or ")" in s or "（" in s or "주)" in s:
        return False
    # Mostly-Korean: at least half the non-space chars are Hangul.
    compact = s.replace(" ", "")
    return len(hangul) >= max(2, len(compact) // 2)


def extract_spec_labels(xlsx_path: Path, out_dir: Path, ocr=ocr_image) -> tuple[list[str], dict]:
    """Extract the screen-layout screenshot labels. ``ocr`` is injectable so the
    comparison logic can be tested without the platform Vision dependency.

    Returns (labels, meta) where meta records the OCR engine, availability, the
    images read, and any skipped vector images."""
    images, skipped = extract_spec_images(xlsx_path, out_dir)
    available = ocr_available()
    labels: list[str] = []
    seen: set[str] = set()
    for img in images:
        for line in ocr(img):
            if is_label(line) and line not in seen:
                seen.add(line)
                labels.append(line)
    meta = {
        "ocr_engine": _OCR_ENGINE,
        "ocr_available": available,
        "images_read": [p.name for p in images],
        "images_skipped": skipped,
    }
    return labels, meta
