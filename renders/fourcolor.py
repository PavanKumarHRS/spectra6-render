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
#
# COLOR_TO_NIBBLE = {
#     (0, 0, 0):       0x0,   # Black
#     (255, 255, 255): 0x1,   # White
#     (255, 255, 0):   0x2,   # Yellow
#     (255, 0, 0):     0x3,   # Red
# }
#
#
# def render_to_4bpp(image_path: str):
#
#     img = Image.open(image_path).convert("RGB")
#
#     width, height = img.size
#
#     print(f"BMP SIZE = {width} x {height}")
#
#     pixels = list(img.getdata())
#
#     packed = bytearray()
#
#     for i in range(0, len(pixels), 2):
#
#         p0 = COLOR_TO_NIBBLE.get(pixels[i], 0)
#
#         if i + 1 < len(pixels):
#             p1 = COLOR_TO_NIBBLE.get(pixels[i + 1], 0)
#         else:
#             p1 = 0
#
#         packed.append((p0 << 4) | p1)
#
#     print(f"OUTPUT BYTES = {len(packed)}")
#     print(f"EXPECTED     = {(width * height) // 2}")
#
#     return bytes(packed), width, height
#
#
#
# def nearest_palette_color(r, g, b):
#     """
#     Returns (pr, pg, pb)
#     """
#     best = None
#     best_dist = 1 << 60
#
#     palette = [
#         (0, 0, 0),           # Black
#         (255, 255, 255),     # White
#         (255, 255, 0),       # Yellow
#         (255, 0, 0),         # Red
#     ]
#
#     for pr, pg, pb in palette:
#         dr = r - pr
#         dg = g - pg
#         db = b - pb
#         d = dr * dr + dg * dg + db * db
#
#         if d < best_dist:
#             best_dist = d
#             best = (pr, pg, pb)
#
#     return best
#
#
# def clamp(v):
#     if v < 0:
#         return 0
#     if v > 255:
#         return 255
#     return int(v)
#
#
# def dither_four_color(img):
#
#     img = img.convert("RGB")
#
#     width, height = img.size
#
#     pixels = img.load()
#
#     for y in range(height):
#
#         for x in range(width):
#
#             old_r, old_g, old_b = pixels[x, y]
#
#             new_r, new_g, new_b = nearest_palette_color(
#                 old_r,
#                 old_g,
#                 old_b
#             )
#
#             pixels[x, y] = (
#                 new_r,
#                 new_g,
#                 new_b
#             )
#
#             err_r = old_r - new_r
#             err_g = old_g - new_g
#             err_b = old_b - new_b
#
#             # Right
#             if x + 1 < width:
#                 r, g, b = pixels[x + 1, y]
#                 pixels[x + 1, y] = (
#                     clamp(r + err_r * 7 / 16),
#                     clamp(g + err_g * 7 / 16),
#                     clamp(b + err_b * 7 / 16)
#                 )
#
#             # Bottom-left
#             if x > 0 and y + 1 < height:
#                 r, g, b = pixels[x - 1, y + 1]
#                 pixels[x - 1, y + 1] = (
#                     clamp(r + err_r * 3 / 16),
#                     clamp(g + err_g * 3 / 16),
#                     clamp(b + err_b * 3 / 16)
#                 )
#
#             # Bottom
#             if y + 1 < height:
#                 r, g, b = pixels[x, y + 1]
#                 pixels[x, y + 1] = (
#                     clamp(r + err_r * 5 / 16),
#                     clamp(g + err_g * 5 / 16),
#                     clamp(b + err_b * 5 / 16)
#                 )
#
#             # Bottom-right
#             if x + 1 < width and y + 1 < height:
#                 r, g, b = pixels[x + 1, y + 1]
#                 pixels[x + 1, y + 1] = (
#                     clamp(r + err_r * 1 / 16),
#                     clamp(g + err_g * 1 / 16),
#                     clamp(b + err_b * 1 / 16)
#                 )
#
#     return img
#
#
# def render_fourcolor():
#
#     global now
#     t_total_start = time.time()
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
#         img = Image.open(tmp_input_bmp.name).convert("RGB")
#         # Apply your own dithering
#         img = dither_four_color(img)
#         # Save the dithered image
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
#         t_bmp = time.time() - t0
#
#         print(
#             f"[TIME] BMP DOWNLOAD = "
#             f"{t_bmp:.3f}s"
#         )
#
#
#
#         # ============================================
#         # BMP -> HEX
#         # ============================================
#
#         t0 = time.time()
#
#         packed_data, width, height = render_to_4bpp(
#             tmp_input_bmp.name
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
#             f"{color_mode}/FourColoralarm.txt"
#         )
#
#         out_blob = bucket.blob(firebase_path)
#
#         out_blob.content_disposition = (
#             f'attachment; filename="{color_mode}{output_type}.txt"'
#         )
#
#         out_blob.upload_from_string(
#             packed_data,
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
#
#         txt_size = len(packed_data)
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
#
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


