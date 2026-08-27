# from flask import Flask, request, jsonify
#
# import firebase_admin
# from firebase_admin import credentials
# from firebase_admin import storage
#
# from PIL import Image
#
# import subprocess
# import os
# import io
# import time
# import tempfile
# from urllib.parse import quote
#
#
# if not firebase_admin._apps:
#
#     firebase_admin.initialize_app(
#         options={
#             "storageBucket":
#             "epaper-30f1b.firebasestorage.app"
#         }
#     )
#
# bucket = storage.bucket()
#
# # =====================================================
# # CONFIG
# # =====================================================
#
# RENDER_BINARY = "./render_sdk/Spectra6_render_x86_64"
#
# LUT_FILE = (
#     "./render_sdk/bin/"
#     "Spectra6_Render_LUT_6color_Default_v1.bin"
# )
#
# # ── Startup validation — fail fast before first request
#
# if not os.path.exists(RENDER_BINARY):
#     raise RuntimeError(f"RENDER BINARY MISSING: {RENDER_BINARY}")
#
# if not os.path.exists(LUT_FILE):
#     raise RuntimeError(f"LUT FILE MISSING: {LUT_FILE}")
#
# os.chmod(RENDER_BINARY, 0o755)
#
# # (r, g, b, hex_string)
# PALETTE = [
#     (  0,   0,   0, "00"),   # BLACK
#     (255, 255, 255, "01"),   # WHITE
#     (255, 255,   0, "02"),   # YELLOW
#     (255,   0,   0, "03"),   # RED
#     (  0,   0, 255, "05"),   # BLUE
#     (  0, 255,   0, "06"),   # GREEN
# ]
#
# _COLOR_CACHE: dict = {}
#
#
# def get_color_hex(r: int, g: int, b: int) -> str:
#     """
#     Nearest-color palette match, quantized-key cached.
#     Returns 2-char hex string e.g. '00', 'FF', '02'.
#     """
#
#     key = (r >> 4, g >> 4, b >> 4)
#
#     result = _COLOR_CACHE.get(key)
#     if result is not None:
#         return result
#
#     best_hex = "01"
#     min_dist = 2147483647
#
#     for pr, pg, pb, hx in PALETTE:
#         dr = r - pr
#         dg = g - pg
#         db = b - pb
#         dist = dr * dr + dg * dg + db * db
#         if dist < min_dist:
#             min_dist = dist
#             best_hex = hx
#
#     _COLOR_CACHE[key] = best_hex
#     return best_hex
#
#
# def render_to_hex(rendered_bmp_path: str):
#
#     img    = Image.open(rendered_bmp_path)
#     img    = img.convert("RGB")
#
#     width, height = img.size
#     total         = width * height
#
#     print(f"BMP SIZE     = {width} x {height}")
#     print(f"TOTAL PIXELS = {total}")
#
#     pixels = img.getdata()
#
#     parts = [""] * total
#
#     for i, (r, g, b) in enumerate(pixels):
#         parts[i] = get_color_hex(r, g, b)
#
#     hex_string = "".join(parts)
#
#     print(f"HEX LENGTH   = {len(hex_string)}")
#     print(f"EXPECTED     = {total * 2}")
#
#     return hex_string, width, height
#
# def render_sixcolor():
#
#     t_total_start  = time.time()
#     tmp_input_bmp  = None
#     tmp_output_bmp = None
#
#     try:
#
#         # -------------------------------------------------
#         # PARAMS
#         # -------------------------------------------------
#
#         body = request.get_json(force=True, silent=True) or {}
#
#         image_path = (
#             body.get("imagePath") or
#             request.args.get("imagePath")
#         )
#
#         user_id = (
#             body.get("userId") or
#             request.args.get("userId") or
#             "A2XX1"
#         )
#
#         if not image_path:
#             return jsonify({"error": "imagePath required"}), 400
#
#         print("=" * 52)
#         print(f"IMAGE PATH   = {image_path}")
#         print(f"USER ID      = {user_id}")
#
#         # -------------------------------------------------
#         # DOWNLOAD PNG FROM FIREBASE → memory
#         # Skips intermediate PNG temp file entirely.
#         # -------------------------------------------------
#
#         t0 = time.time()
#
#         blob = bucket.blob(image_path)
#
#         if not blob.exists():
#             return jsonify({"error": "image not found in Firebase"}), 404
#
#         png_bytes  = blob.download_as_bytes()
#         t_download = time.time() - t0
#
#         print(f"[TIME] DOWNLOAD    = {t_download:.3f}s  ({len(png_bytes):,} bytes)")
#
#         # -------------------------------------------------
#         # PNG → BMP (temp file — SDK needs file path)
#         # -------------------------------------------------
#
#         t0 = time.time()
#
#         image = Image.open(io.BytesIO(png_bytes))
#         image = image.convert("RGB")
#
#         w, h = image.size
#
#         if w <= 0 or h <= 0:
#             return jsonify({"error": "invalid image dimensions"}), 400
#
#         print(f"IMAGE SIZE   = {w} x {h}")
#
#         tmp_input_bmp = tempfile.NamedTemporaryFile(
#             suffix=".bmp", delete=False
#         )
#         tmp_input_bmp.close()
#
#         image.save(tmp_input_bmp.name, format="BMP")
#
#         # Free RAM immediately — no longer needed
#         del image
#         del png_bytes
#
#         tmp_output_bmp = tempfile.NamedTemporaryFile(
#             suffix=".bmp", delete=False
#         )
#         tmp_output_bmp.close()
#
#         t_bmp = time.time() - t0
#         print(f"[TIME] BMP CONVERT = {t_bmp:.3f}s")
#
#
#         t0 = time.time()
#
#         cmd = [
#             RENDER_BINARY,
#             "-i", tmp_input_bmp.name,
#             "-o", tmp_output_bmp.name,
#             "-l", LUT_FILE,
#             "-d", "1",
#             "-m", "2"
#         ]
#
#         print(f"CMD          = {' '.join(cmd)}")
#
#         env                    = os.environ.copy()
#         env["LD_LIBRARY_PATH"] = "/app/render_sdk/lib"
#
#         result = subprocess.run(
#             cmd,
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             text=True,
#             env=env,
#             timeout=60
#         )
#
#         t_render = time.time() - t0
#         print(f"[TIME] RENDER      = {t_render:.3f}s")
#         print(f"RETURN CODE  = {result.returncode}")
#
#         if result.stdout.strip():
#             print("STDOUT:", result.stdout.strip())
#         if result.stderr.strip():
#             print("STDERR:", result.stderr.strip())
#
#         # Validate output exists and is non-empty
#         output_ok = (
#             result.returncode == 0 and
#             os.path.exists(tmp_output_bmp.name) and
#             os.path.getsize(tmp_output_bmp.name) > 0
#         )
#
#         if not output_ok:
#             return jsonify({
#                 "status":     "render_failed",
#                 "returncode": result.returncode,
#                 "stdout":     result.stdout,
#                 "stderr":     result.stderr
#             }), 500
#
#         print("RENDER       = SUCCESS")
#
#         # -------------------------------------------------
#         # BMP → HEX STRING
#         # -------------------------------------------------
#
#         t0 = time.time()
#
#         hex_string, width, height = render_to_hex(
#             tmp_output_bmp.name
#         )
#
#         t_hex = time.time() - t0
#         print(f"[TIME] HEX CONVERT = {t_hex:.3f}s")
#
#         t0 = time.time()
#
#         firebase_path = (
#             f"users/{user_id}/SixColor/SixColoralarm.txt"
#         )
#
#         out_blob = bucket.blob(firebase_path)
#
#         out_blob.content_disposition = (
#             'attachment; filename="SixColoralarm.txt"'
#         )
#
#         out_blob.upload_from_string(
#             hex_string.encode("ascii"),
#             content_type="application/octet-stream"
#         )
#
#         t_upload = time.time() - t0
#         print(f"[TIME] UPLOAD      = {t_upload:.3f}s")
#         print(f"FIREBASE PATH= {firebase_path}")
#
#         # -------------------------------------------------
#         # DOWNLOAD URL
#         # -------------------------------------------------
#
#         download_url = (
#             f"https://firebasestorage.googleapis.com/v0/b/"
#             f"{bucket.name}/o/"
#             f"{quote(firebase_path, safe='')}"
#             f"?alt=media"
#         )
#
#         txt_size = len(hex_string)
#         t_total  = time.time() - t_total_start
#
#         print(f"[TIME] TOTAL       = {t_total:.3f}s")
#         print("=" * 52)
#
#         # -------------------------------------------------
#         # RESPONSE
#         # -------------------------------------------------
#
#         return jsonify({
#             "status":       "success",
#             "downloadUrl":  download_url,
#             "firebasePath": firebase_path,
#             "width":        width,
#             "height":       height,
#             "txtSize":      txt_size,
#             "hexLength":    txt_size,
#             "totalTimeSec": round(t_total, 3),
#             "timings": {
#                 "downloadSec":   round(t_download, 3),
#                 "bmpConvertSec": round(t_bmp,      3),
#                 "renderSec":     round(t_render,    3),
#                 "hexConvertSec": round(t_hex,       3),
#                 "uploadSec":     round(t_upload,    3)
#             }
#         })
#
#     except subprocess.TimeoutExpired:
#         print("[ERROR] Render timeout")
#         return jsonify({"error": "render timeout after 60s"}), 500
#
#     except Exception as e:
#         print(f"[ERROR] {e}")
#         return jsonify({"error": str(e)}), 500
#
#     finally:
#
#         for f in [tmp_input_bmp, tmp_output_bmp]:
#             try:
#                 if f and os.path.exists(f.name):
#                     os.remove(f.name)
#             except Exception:
#                 pass
#
#         # Prevent cache from growing unbounded
#         if len(_COLOR_CACHE) > 8192:
#             _COLOR_CACHE.clear()


#non auth find
# from flask import Flask, request, jsonify
#
# import firebase_admin
# from firebase_admin import credentials
# from firebase_admin import storage
# from firebase_admin import firestore
# from datetime import datetime
# from zoneinfo import ZoneInfo
#
# from PIL import Image
#
# import subprocess
# import os
# import io
# import time
# import tempfile
# from urllib.parse import quote
#
#
# if not firebase_admin._apps:
#
#     firebase_admin.initialize_app(
#         options={
#             "storageBucket":
#             "epaper-30f1b.firebasestorage.app"
#         }
#     )
#
# bucket = storage.bucket()
# db = firestore.client()
#
# # =====================================================
# # CONFIG
# # =====================================================
#
# RENDER_BINARY = "./render_sdk/Spectra6_render_x86_64"
#
# LUT_FILE = (
#     "./render_sdk/bin/"
#     "Spectra6_Render_LUT_6color_Default_v1.bin"
# )
#
# # ── Startup validation — fail fast before first request
#
# if not os.path.exists(RENDER_BINARY):
#     raise RuntimeError(f"RENDER BINARY MISSING: {RENDER_BINARY}")
#
# if not os.path.exists(LUT_FILE):
#     raise RuntimeError(f"LUT FILE MISSING: {LUT_FILE}")
#
# os.chmod(RENDER_BINARY, 0o755)
#
# # (r, g, b, hex_string)
# PALETTE = [
#     (  0,   0,   0, "00"),   # BLACK
#     (255, 255, 255, "ff"),   # WHITE
#     (255, 255,   0, "e2"),   # YELLOW
#     (255,   0,   0, "4c"),   # RED
#     (  0,   0, 255, "1d"),   # BLUE
#     (  0, 255,   0, "96"),   # GREEN
# ]
#
# _COLOR_CACHE: dict = {}
#
#
# def get_color_hex(r: int, g: int, b: int) -> str:
#     """
#     Nearest-color palette match, quantized-key cached.
#     Returns 2-char hex string e.g. '00', 'FF', '02'.
#     """
#
#     key = (r >> 4, g >> 4, b >> 4)
#
#     result = _COLOR_CACHE.get(key)
#     if result is not None:
#         return result
#
#     best_hex = "01"
#     min_dist = 2147483647
#
#     for pr, pg, pb, hx in PALETTE:
#         dr = r - pr
#         dg = g - pg
#         db = b - pb
#         dist = dr * dr + dg * dg + db * db
#         if dist < min_dist:
#             min_dist = dist
#             best_hex = hx
#
#     _COLOR_CACHE[key] = best_hex
#     return best_hex
#
# def render_to_hex(rendered_bmp_path: str):
#
#     img    = Image.open(rendered_bmp_path)
#     img    = img.convert("RGB")
#
#     width, height = img.size
#     total         = width * height
#
#     print(f"BMP SIZE     = {width} x {height}")
#     print(f"TOTAL PIXELS = {total}")
#
#     pixels = img.getdata()
#
#     parts = [""] * total
#
#     for i, (r, g, b) in enumerate(pixels):
#         parts[i] = get_color_hex(r, g, b)
#
#     hex_string = "".join(parts)
#
#     print(f"HEX LENGTH   = {len(hex_string)}")
#     print(f"EXPECTED     = {total * 2}")
#
#     return hex_string, width, height
#
# def render_sixcolor():
#
#     global now
#     t_total_start = time.time()
#     tmp_input_bmp = None
#     tmp_output_bmp = None
#
#     try:
#
#         body = request.get_json(force=True, silent=True) or {}
#
#         user_id = (
#             body.get("userId")
#             or request.args.get("userId")
#             or "7FXX1"
#         )
#
#         color_mode = (
#             body.get("colorMode")
#             or request.args.get("colorMode")
#             or "SixColor"
#         )
#
#         print("=" * 60)
#         print(f"USER ID    = {user_id}")
#         print(f"COLOR MODE = {color_mode}")
#
#         # ============================================
#         # CHECK ALARM
#         # ============================================
#
#         active_alarm = None
#
#         alarm_doc = (
#             db.collection("users")
#             .document(user_id)
#             .collection("modes")
#             .document(color_mode)
#             .get()
#         )
#
#         if alarm_doc.exists:
#
#             alarm_data = alarm_doc.to_dict()
#
#             now = datetime.now(
#                 ZoneInfo("Asia/Kolkata")
#             )
#
#             for alarm_name in ["alarm1", "alarm2", "alarm3"]:
#
#                 alarm_time = alarm_data.get(alarm_name)
#
#                 if not alarm_time:
#                     continue
#
#                 try:
#
#                     alarm_dt = datetime.strptime(
#                         alarm_time,
#                         "%H:%M"
#                     )
#
#                     alarm_minutes = (
#                         alarm_dt.hour * 60 +
#                         alarm_dt.minute
#                     )
#
#                     now_minutes = (
#                         now.hour * 60 +
#                         now.minute
#                     )
#
#                     diff = now_minutes - alarm_minutes
#
#                     if 0 <= diff <= 2:
#                         active_alarm = alarm_name
#                         break
#
#                 except Exception as e:
#                     print(f"Alarm Parse Error: {e}")
#
#         # ============================================
#         # IMAGE PATH
#         # ============================================
#
#         if active_alarm:
#
#             today = now.strftime("%Y%m%d")
#
#             image_path = (
#                 f"users/{user_id}/images/"
#                 f"{color_mode}/Frame/{active_alarm}/{today}.bmp"
#             )
#
#             output_type = "alarm"
#
#         else:
#
#             print("NO ALARM MATCHED -> USING MANUAL")
#
#             image_path = (
#                 f"users/{user_id}/images/"
#                 f"{color_mode}/Frame/input.bmp"
#             )
#
#             output_type = "manual"
#
#         print(f"IMAGE PATH = {image_path}")
#
#         # ============================================
#         # DOWNLOAD BMP
#         # ============================================
#
#         t0 = time.time()
#
#         blob = bucket.blob(image_path)
#
#         if not blob.exists():
#             return jsonify({
#                 "error": "image not found",
#                 "imagePath": image_path
#             }), 404
#
#         tmp_input_bmp = tempfile.NamedTemporaryFile(
#             suffix=".bmp",
#             delete=False
#         )
#         tmp_input_bmp.close()
#
#         blob.download_to_filename(
#             tmp_input_bmp.name
#         )
#
#         img = Image.open(tmp_input_bmp.name)
#         img = img.convert("RGB")
#         img.save(tmp_input_bmp.name, format="BMP")
#
#         print("IMAGE PATH =", image_path)
#         print("LOCAL BMP =", tmp_input_bmp.name)
#         print("FILE SIZE =", os.path.getsize(tmp_input_bmp.name))
#
#         img = Image.open(tmp_input_bmp.name)
#         print("MODE =", img.mode)
#         print("SIZE =", img.size)
#
#         tmp_output_bmp = tempfile.NamedTemporaryFile(
#             suffix=".bmp",
#             delete=False
#         )
#         tmp_output_bmp.close()
#
#         t_bmp = time.time() - t0
#
#         print(
#             f"[TIME] BMP DOWNLOAD = "
#             f"{t_bmp:.3f}s"
#         )
#
#         # ============================================
#         # RENDER
#         # ============================================
#
#         t0 = time.time()
#
#         cmd = [
#             RENDER_BINARY,
#             "-i", tmp_input_bmp.name,
#             "-o", tmp_output_bmp.name,
#             "-l", LUT_FILE,
#             "-d", "1",
#             "-m", "2"
#         ]
#
#         env = os.environ.copy()
#         env["LD_LIBRARY_PATH"] = "/app/render_sdk/lib"
#
#         result = subprocess.run(
#             cmd,
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             text=True,
#             env=env,
#             timeout=60
#         )
#
#         print("RETURN CODE =", result.returncode)
#         print("STDOUT =", result.stdout)
#         print("STDERR =", result.stderr)
#
#         if os.path.exists(tmp_output_bmp.name):
#             print(
#                 "OUTPUT SIZE =",
#                 os.path.getsize(tmp_output_bmp.name)
#             )
#
#         t_render = time.time() - t0
#
#         print(f"[TIME] RENDER = {t_render:.3f}s")
#
#         if result.returncode != 0:
#             return jsonify({
#                 "status": "render_failed",
#                 "stdout": result.stdout,
#                 "stderr": result.stderr
#             }), 500
#
#         # ============================================
#         # BMP -> HEX
#         # ============================================
#
#         t0 = time.time()
#
#         hex_string, width, height = render_to_hex(
#             tmp_output_bmp.name
#         )
#
#         t_hex = time.time() - t0
#
#         print(
#             f"[TIME] HEX CONVERT = "
#             f"{t_hex:.3f}s"
#         )
#
#         # ============================================
#         # UPLOAD TXT
#         # ============================================
#
#         t0 = time.time()
#
#         firebase_path = (
#             f"users/{user_id}/"
#             f"{color_mode}/"
#             f"{color_mode}{output_type}.txt"
#         )
#
#         out_blob = bucket.blob(firebase_path)
#
#         out_blob.content_disposition = (
#             f'attachment; filename="{color_mode}{output_type}.txt"'
#         )
#
#         out_blob.upload_from_string(
#             hex_string.encode("ascii"),
#             content_type="application/octet-stream"
#         )
#
#         t_upload = time.time() - t0
#
#         print(f"[TIME] UPLOAD = {t_upload:.3f}s")
#         print(f"FIREBASE PATH = {firebase_path}")
#
#         # ============================================
#         # URL
#         # ============================================
#
#         download_url = (
#             f"https://firebasestorage.googleapis.com/v0/b/"
#             f"{bucket.name}/o/"
#             f"{quote(firebase_path, safe='')}"
#             f"?alt=media"
#         )
#
#         txt_size = len(hex_string)
#         t_total = time.time() - t_total_start
#
#         print(f"[TIME] TOTAL = {t_total:.3f}s")
#         print("=" * 60)
#
#         return jsonify({
#             "status": "success",
#             "outputType": output_type,
#             "alarm": active_alarm,
#             "downloadUrl": download_url,
#             "firebasePath": firebase_path,
#             "width": width,
#             "height": height,
#             "txtSize": txt_size,
#             "hexLength": txt_size,
#             "totalTimeSec": round(t_total, 3),
#             "timings": {
#                 "bmpDownloadSec": round(t_bmp, 3),
#                 "renderSec": round(t_render, 3),
#                 "hexConvertSec": round(t_hex, 3),
#                 "uploadSec": round(t_upload, 3)
#             }
#         })
#
#     except subprocess.TimeoutExpired:
#         return jsonify({
#             "error": "render timeout after 60s"
#         }), 500
#
#     except Exception as e:
#         print(f"[ERROR] {e}")
#         return jsonify({
#             "error": str(e)
#         }), 500
#
#     finally:
#
#         for f in [tmp_input_bmp, tmp_output_bmp]:
#             try:
#                 if f and os.path.exists(f.name):
#                     os.remove(f.name)
#             except:
#                 pass
#
#         if len(_COLOR_CACHE) > 8192:
#             _COLOR_CACHE.clear()

#auth

from flask import Flask, request, jsonify

import firebase_admin
from firebase_admin import credentials
from firebase_admin import storage
from firebase_admin import firestore
from datetime import datetime
from zoneinfo import ZoneInfo

from PIL import Image

import subprocess
import os
import io
import time
import tempfile
from urllib.parse import quote


if not firebase_admin._apps:

    firebase_admin.initialize_app(
        options={
            "storageBucket":
            "epaper-30f1b.firebasestorage.app"
        }
    )

# from renders.pdf_handler_sixcolor import create_alarm_bmp

bucket = storage.bucket()
db = firestore.client()

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

# (r, g, b, hex_string)
PALETTE = [
    (  0,   0,   0, "00"),   # BLACK
    (255, 255, 255, "ff"),   # WHITE
    (255, 255,   0, "e2"),   # YELLOW
    (255,   0,   0, "4c"),   # RED
    (  0,   0, 255, "1d"),   # BLUE
    (  0, 255,   0, "96"),   # GREEN
]

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


def get_auth_uid(device_id):

    doc = (
        db.collection("deviceOwners")
        .document(device_id)
        .get()
    )

    if not doc.exists:
        raise Exception(f"Device {device_id} not found")

    data = doc.to_dict()

    auth_uid = data.get("authUid")

    if not auth_uid:
        raise Exception("authUid missing")

    return auth_uid

def get_device_orientation(auth_uid, device_id, device_type):

    # Only check orientation for TwoSide device
    if str(device_type).strip().lower() != "twoside":
        return None

    device_doc = (
        db.collection("users")
        .document(auth_uid)
        .collection("devices")
        .document(device_id)
        .get()
    )

    if not device_doc.exists:
        raise Exception(f"Device {device_id} not found")

    data = device_doc.to_dict() or {}

    # Read deviceOrientation from Firestore
    orientation = data.get("deviceOrientation")

    if not orientation:
        raise Exception(
            "deviceOrientation missing for TwoSide device"
        )

    orientation = str(orientation).strip().lower()

    # Only landscape / portrait allowed
    if orientation not in ["landscape", "portrait"]:
        raise Exception(
            f"Invalid deviceOrientation: {orientation}"
        )

    print("DEVICE TYPE =", device_type)
    print("DEVICE ORIENTATION =", orientation)

    return orientation

def render_sixcolor():

    global now
    t_total_start = time.time()
    tmp_input_bmp = None
    tmp_output_bmp = None

    try:

        body = request.get_json(force=True, silent=True) or {}

        device_id = (
                body.get("userId")
                or request.args.get("userId")
                or "7FTK2"
        )

        auth_uid = get_auth_uid(device_id)

        print("DEVICE ID =", device_id)
        print("AUTH UID  =", auth_uid)

        color_mode = (
            body.get("colorMode")
            or request.args.get("colorMode")
            or "SixColor"
        )

        # device_type = (
        #         body.get("device_type")
        #         or request.args.get("device_type")
        #         or "1side"
        # )
        #
        # print("=" * 60)
        # print(f"USER ID    = {device_id}")
        # print(f"COLOR MODE = {color_mode}")
        # print(f"DEVICE TYPE = {device_type}")

        device_type = (
                body.get("device_type")
                or request.args.get("device_type")
                or "1side"
        )

        # Get orientation only when device type is TwoSide
        device_orientation = get_device_orientation(
            auth_uid,
            device_id,
            device_type
        )

        print("=" * 60)
        print(f"USER ID            = {device_id}")
        print(f"COLOR MODE         = {color_mode}")
        print(f"DEVICE TYPE        = {device_type}")
        print(f"DEVICE ORIENTATION = {device_orientation}")


        # CHECK ALARM

        active_alarm = None

        alarm_doc = (
            db.collection("users")
            .document(auth_uid)
            .collection("devices")
            .document(device_id)
            .collection("modes")
            .document(color_mode)
            .get()
        )

        if alarm_doc.exists:

            alarm_data = alarm_doc.to_dict()

            now = datetime.now(
                ZoneInfo("Asia/Kolkata")
            )

            for alarm_name in ["alarm1", "alarm2", "alarm3"]:

                alarm_time = alarm_data.get(alarm_name)

                if not alarm_time:
                    continue

                try:

                    alarm_dt = datetime.strptime(
                        alarm_time,
                        "%H:%M"
                    )

                    alarm_minutes = (
                        alarm_dt.hour * 60 +
                        alarm_dt.minute
                    )

                    now_minutes = (
                        now.hour * 60 +
                        now.minute
                    )

                    diff = now_minutes - alarm_minutes

                    if 0 <= diff <= 2:
                        active_alarm = alarm_name
                        break

                    # if 0 <= diff <= 2:
                    #
                    #     active_alarm = alarm_name
                    #
                    #     if alarm_name == "alarm1":
                    #         create_alarm_bmp(
                    #             auth_uid=auth_uid,
                    #             device_id=device_id,
                    #             color_mode=color_mode
                    #         )
                    #
                    #     break

                except Exception as e:
                    print(f"Alarm Parse Error: {e}")

        # IMAGE PATH

        if active_alarm:

            today = now.strftime("%Y%m%d")

            image_path = (
                f"users/{auth_uid}/devices/{device_id}/"
                f"images/{color_mode}/Frame/"
                f"{active_alarm}/{today}.bmp"
            )

            output_type = "alarm"

        else:

            print("NO ALARM MATCHED -> USING MANUAL")

            image_path = (
                f"users/{auth_uid}/devices/{device_id}/"
                f"images/{color_mode}/Frame/manual.bmp"
            )

            output_type = "manual"

        print(f"IMAGE PATH = {image_path}")

        # DOWNLOAD BMP

        t0 = time.time()

        blob = bucket.blob(image_path)

        if not blob.exists():
            return jsonify({
                "error": "image not found",
                "imagePath": image_path
            }), 404

        tmp_input_bmp = tempfile.NamedTemporaryFile(
            suffix=".bmp",
            delete=False
        )
        tmp_input_bmp.close()

        blob.download_to_filename(
            tmp_input_bmp.name
        )

        img = Image.open(tmp_input_bmp.name)
        img = img.convert("RGB")
        img.save(tmp_input_bmp.name, format="BMP")

        print("IMAGE PATH =", image_path)
        print("LOCAL BMP =", tmp_input_bmp.name)
        print("FILE SIZE =", os.path.getsize(tmp_input_bmp.name))

        img = Image.open(tmp_input_bmp.name)
        print("MODE =", img.mode)
        print("SIZE =", img.size)

        tmp_output_bmp = tempfile.NamedTemporaryFile(
            suffix=".bmp",
            delete=False
        )
        tmp_output_bmp.close()

        t_bmp = time.time() - t0

        print(
            f"[TIME] BMP DOWNLOAD = "
            f"{t_bmp:.3f}s"
        )


        # RENDER

        t0 = time.time()

        cmd = [
            RENDER_BINARY,
            "-i", tmp_input_bmp.name,
            "-o", tmp_output_bmp.name,
            "-l", LUT_FILE,
            "-d", "1",
            "-m", "2"
        ]

        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = "/app/render_sdk/lib"

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            timeout=60
        )

        print("RETURN CODE =", result.returncode)
        print("STDOUT =", result.stdout)
        print("STDERR =", result.stderr)

        if os.path.exists(tmp_output_bmp.name):
            print(
                "OUTPUT SIZE =",
                os.path.getsize(tmp_output_bmp.name)
            )

        t_render = time.time() - t0

        print(f"[TIME] RENDER = {t_render:.3f}s")

        if result.returncode != 0:
            return jsonify({
                "status": "render_failed",
                "stdout": result.stdout,
                "stderr": result.stderr
            }), 500


        # BMP -> HEX

        t0 = time.time()

        hex_string, width, height = render_to_hex(
            tmp_output_bmp.name
        )

        t_hex = time.time() - t0

        print(
            f"[TIME] HEX CONVERT = "
            f"{t_hex:.3f}s"
        )


        # UPLOAD TXT

        t0 = time.time()

        firebase_path = (
            f"users/{auth_uid}/devices/{device_id}/"
            f"{color_mode}/"
            f"{color_mode}{output_type}.txt"
        )

        out_blob = bucket.blob(firebase_path)

        out_blob.content_disposition = (
            f'attachment; filename="{color_mode}{output_type}.txt"'
        )

        out_blob.upload_from_string(
            hex_string.encode("ascii"),
            content_type="application/octet-stream"
        )

        t_upload = time.time() - t0

        print(f"[TIME] UPLOAD = {t_upload:.3f}s")
        print(f"FIREBASE PATH = {firebase_path}")


        # URL

        download_url = (
            f"https://firebasestorage.googleapis.com/v0/b/"
            f"{bucket.name}/o/"
            f"{quote(firebase_path, safe='')}"
            f"?alt=media"
        )

        txt_size = len(hex_string)
        t_total = time.time() - t_total_start

        print(f"[TIME] TOTAL = {t_total:.3f}s")
        print("=" * 60)

        return jsonify({
            "status": "success",

            "deviceId": device_id,
            "deviceType": device_type,
            "deviceOrientation": device_orientation,

            "outputType": output_type,
            "alarm": active_alarm,
            "downloadUrl": download_url,
            "firebasePath": firebase_path,
            "width": width,
            "height": height,
            "txtSize": txt_size,
            "hexLength": txt_size,
            "totalTimeSec": round(t_total, 3),
            "timings": {
                "bmpDownloadSec": round(t_bmp, 3),
                "renderSec": round(t_render, 3),
                "hexConvertSec": round(t_hex, 3),
                "uploadSec": round(t_upload, 3)
            }
        })

    except subprocess.TimeoutExpired:
        return jsonify({
            "error": "render timeout after 60s"
        }), 500

    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({
            "error": str(e)
        }), 500

    finally:

        for f in [tmp_input_bmp, tmp_output_bmp]:
            try:
                if f and os.path.exists(f.name):
                    os.remove(f.name)
            except:
                pass

        if len(_COLOR_CACHE) > 8192:
            _COLOR_CACHE.clear()




