from flask import Flask, request, jsonify

import firebase_admin
from firebase_admin import credentials
from firebase_admin import storage

from PIL import Image

import subprocess
import os
import io
import time
import tempfile
from urllib.parse import quote

# =====================================================
# FLASK
# =====================================================

#app = Flask(__name__)

# =====================================================
# FIREBASE INIT
# =====================================================

cred = credentials.Certificate(
    "firebase/serviceAccount.json"
)

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        "storageBucket": "epaper-30f1b.firebasestorage.app"
    })

bucket = storage.bucket()

# =====================================================
# CONFIG
# =====================================================

RENDER_BINARY = "./render_sdk/Spectra6_render_x86_64"

LUT_FILE = (
    "./render_sdk/bin/"
    "Spectra6_Render_LUT_6color_Default_v1.bin"
)

# ── Startup validation — fail fast before first request

if not os.path.exists(RENDER_BINARY):
    raise RuntimeError(f"RENDER BINARY MISSING: {RENDER_BINARY}")

if not os.path.exists(LUT_FILE):
    raise RuntimeError(f"LUT FILE MISSING: {LUT_FILE}")

os.chmod(RENDER_BINARY, 0o755)

# =====================================================
# COLOR PALETTE
#
# Exact Android getColorIndex() mapping:
#   00 = BLACK
#   01 = WHITE  (fallback)
#   02 = YELLOW
#   03 = RED
#   05 = BLUE
#   06 = GREEN
#
# Nearest-color by squared Euclidean RGB distance.
# Output: 2-char uppercase hex per pixel.
# Matches Java: String.format("%02X", best)
# =====================================================

# (r, g, b, hex_string)
PALETTE = [
    (  0,   0,   0, "00"),   # BLACK
    (255, 255, 255, "01"),   # WHITE
    (255, 255,   0, "02"),   # YELLOW
    (255,   0,   0, "03"),   # RED
    (  0,   0, 255, "05"),   # BLUE
    (  0, 255,   0, "06"),   # GREEN
]

# Quantized cache: each RGB channel >> 4 gives 16 levels
# → 16^3 = 4096 possible keys. Covers all 6 pure render
# output colors on the very first 6 lookups. Zero miss
# after warmup since rendered BMP has only pure palette
# pixels. Much faster than hashing full RGB tuples.

_COLOR_CACHE: dict = {}


def get_color_hex(r: int, g: int, b: int) -> str:
    """
    Nearest-color palette match, quantized-key cached.
    Returns 2-char hex string e.g. '00', 'FF', '02'.
    """

    key = (r >> 4, g >> 4, b >> 4)

    result = _COLOR_CACHE.get(key)
    if result is not None:
        return result

    best_hex = "01"
    min_dist = 2147483647

    for pr, pg, pb, hx in PALETTE:
        dr = r - pr
        dg = g - pg
        db = b - pb
        dist = dr * dr + dg * dg + db * db
        if dist < min_dist:
            min_dist = dist
            best_hex = hx

    _COLOR_CACHE[key] = best_hex
    return best_hex

# =====================================================
# RENDERED BMP -> HEX STRING
#
# Reads render SDK output BMP.
# Each pixel → 2-char hex color index string.
# Pre-allocated list + single join = fastest build.
# Expected length = width * height * 2 chars.
# =====================================================

def render_to_hex(rendered_bmp_path: str):

    img    = Image.open(rendered_bmp_path)
    img    = img.convert("RGB")

    width, height = img.size
    total         = width * height

    print(f"BMP SIZE     = {width} x {height}")
    print(f"TOTAL PIXELS = {total}")

    pixels = img.getdata()

    parts = [""] * total

    for i, (r, g, b) in enumerate(pixels):
        parts[i] = get_color_hex(r, g, b)

    hex_string = "".join(parts)

    print(f"HEX LENGTH   = {len(hex_string)}")
    print(f"EXPECTED     = {total * 2}")

    return hex_string, width, height

# =====================================================
# HOME
# =====================================================

# @app.route("/", methods=["GET"])
# def home():
#     return jsonify({"status": "running"})

# =====================================================
# RENDER
#
# Supports:
#   POST /render                   → JSON body
#   POST /render?userId=X&imagePath=X → URL params
#
# Response JSON:
#   status, downloadUrl, firebasePath,
#   width, height, txtSize, hexLength,
#   totalTimeSec, timings{}
# =====================================================

# @app.route("/render", methods=["POST"])
# def render():

def render_sixcolor():

    t_total_start  = time.time()
    tmp_input_bmp  = None
    tmp_output_bmp = None

    try:

        # -------------------------------------------------
        # PARAMS
        # -------------------------------------------------

        body = request.get_json(force=True, silent=True) or {}

        image_path = (
            body.get("imagePath") or
            request.args.get("imagePath")
        )

        user_id = (
            body.get("userId") or
            request.args.get("userId") or
            "A2XX1"
        )

        if not image_path:
            return jsonify({"error": "imagePath required"}), 400

        print("=" * 52)
        print(f"IMAGE PATH   = {image_path}")
        print(f"USER ID      = {user_id}")

        # -------------------------------------------------
        # DOWNLOAD PNG FROM FIREBASE → memory
        # Skips intermediate PNG temp file entirely.
        # -------------------------------------------------

        t0 = time.time()

        blob = bucket.blob(image_path)

        if not blob.exists():
            return jsonify({"error": "image not found in Firebase"}), 404

        png_bytes  = blob.download_as_bytes()
        t_download = time.time() - t0

        print(f"[TIME] DOWNLOAD    = {t_download:.3f}s  ({len(png_bytes):,} bytes)")

        # -------------------------------------------------
        # PNG → BMP (temp file — SDK needs file path)
        # -------------------------------------------------

        t0 = time.time()

        image = Image.open(io.BytesIO(png_bytes))
        image = image.convert("RGB")

        w, h = image.size

        if w <= 0 or h <= 0:
            return jsonify({"error": "invalid image dimensions"}), 400

        print(f"IMAGE SIZE   = {w} x {h}")

        tmp_input_bmp = tempfile.NamedTemporaryFile(
            suffix=".bmp", delete=False
        )
        tmp_input_bmp.close()

        image.save(tmp_input_bmp.name, format="BMP")

        # Free RAM immediately — no longer needed
        del image
        del png_bytes

        tmp_output_bmp = tempfile.NamedTemporaryFile(
            suffix=".bmp", delete=False
        )
        tmp_output_bmp.close()

        t_bmp = time.time() - t0
        print(f"[TIME] BMP CONVERT = {t_bmp:.3f}s")

        # -------------------------------------------------
        # RUN SPECTRA6 SDK
        #
        # -d 1 = EinkDitheringMethod_EINK_FLOYD_SERPENTINE
        #        Fastest dithering — good quality for 6-color
        # -m 2 = mode_out 2
        # -------------------------------------------------

        t0 = time.time()

        cmd = [
            RENDER_BINARY,
            "-i", tmp_input_bmp.name,
            "-o", tmp_output_bmp.name,
            "-l", LUT_FILE,
            "-d", "1",
            "-m", "2"
        ]

        print(f"CMD          = {' '.join(cmd)}")

        env                    = os.environ.copy()
        env["LD_LIBRARY_PATH"] = "/app/render_sdk/lib"

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            timeout=60
        )

        t_render = time.time() - t0
        print(f"[TIME] RENDER      = {t_render:.3f}s")
        print(f"RETURN CODE  = {result.returncode}")

        if result.stdout.strip():
            print("STDOUT:", result.stdout.strip())
        if result.stderr.strip():
            print("STDERR:", result.stderr.strip())

        # Validate output exists and is non-empty
        output_ok = (
            result.returncode == 0 and
            os.path.exists(tmp_output_bmp.name) and
            os.path.getsize(tmp_output_bmp.name) > 0
        )

        if not output_ok:
            return jsonify({
                "status":     "render_failed",
                "returncode": result.returncode,
                "stdout":     result.stdout,
                "stderr":     result.stderr
            }), 500

        print("RENDER       = SUCCESS")

        # -------------------------------------------------
        # BMP → HEX STRING
        # -------------------------------------------------

        t0 = time.time()

        hex_string, width, height = render_to_hex(
            tmp_output_bmp.name
        )

        t_hex = time.time() - t0
        print(f"[TIME] HEX CONVERT = {t_hex:.3f}s")

        # -------------------------------------------------
        # UPLOAD TO FIREBASE
        # Encode to ASCII bytes — no UTF-8 overhead
        # since output is pure hex chars 0-9 A-F.
        # -------------------------------------------------

        t0 = time.time()

        firebase_path = (
            f"users/{user_id}/SixColorA2/SixColoralarm.txt"
        )

        out_blob = bucket.blob(firebase_path)

        out_blob.content_disposition = (
            'attachment; filename="SixColoralarm.txt"'
        )

        out_blob.upload_from_string(
            hex_string.encode("ascii"),
            content_type="application/octet-stream"
        )

        t_upload = time.time() - t0
        print(f"[TIME] UPLOAD      = {t_upload:.3f}s")
        print(f"FIREBASE PATH= {firebase_path}")

        # -------------------------------------------------
        # DOWNLOAD URL
        # -------------------------------------------------

        download_url = (
            f"https://firebasestorage.googleapis.com/v0/b/"
            f"{bucket.name}/o/"
            f"{quote(firebase_path, safe='')}"
            f"?alt=media"
        )

        txt_size = len(hex_string)
        t_total  = time.time() - t_total_start

        print(f"[TIME] TOTAL       = {t_total:.3f}s")
        print("=" * 52)

        # -------------------------------------------------
        # RESPONSE
        # -------------------------------------------------

        return jsonify({
            "status":       "success",
            "downloadUrl":  download_url,
            "firebasePath": firebase_path,
            "width":        width,
            "height":       height,
            "txtSize":      txt_size,
            "hexLength":    txt_size,
            "totalTimeSec": round(t_total, 3),
            "timings": {
                "downloadSec":   round(t_download, 3),
                "bmpConvertSec": round(t_bmp,      3),
                "renderSec":     round(t_render,    3),
                "hexConvertSec": round(t_hex,       3),
                "uploadSec":     round(t_upload,    3)
            }
        })

    except subprocess.TimeoutExpired:
        print("[ERROR] Render timeout")
        return jsonify({"error": "render timeout after 60s"}), 500

    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({"error": str(e)}), 500

    finally:

        for f in [tmp_input_bmp, tmp_output_bmp]:
            try:
                if f and os.path.exists(f.name):
                    os.remove(f.name)
            except Exception:
                pass

        # Prevent cache from growing unbounded
        if len(_COLOR_CACHE) > 8192:
            _COLOR_CACHE.clear()

# =====================================================
# MAIN — local dev only
# Production deploy:
#   gunicorn server:app --workers 2 --timeout 120
# =====================================================

# if __name__ == "__main__":
#
#     port = int(os.environ.get("PORT", 8080))
#
#     app.run(
#         host="0.0.0.0",
#         port=port,
#         debug=False
#     )