from flask import Flask, request, jsonify

import firebase_admin
from firebase_admin import credentials
from firebase_admin import storage
from firebase_admin import firestore

from PIL import Image
from datetime import datetime
from zoneinfo import ZoneInfo
import subprocess
import os
import io
import time
import tempfile
from urllib.parse import quote
from PIL import Image, ImageEnhance

from renders.calendar_overlay import add_calendar_overlay
from renders.weather_api import get_weather_data

if not firebase_admin._apps:

    firebase_admin.initialize_app(
        options={
            "storageBucket":
            "epaper-30f1b.firebasestorage.app"
        }
    )


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
    (0,0,0,"0"),
    (255,255,255,"1"),
    (255,255,0,"2"),
    (255,0,0,"3"),
    (0,0,255,"5"),
    (0,255,0,"6"),
]

_COLOR_CACHE: dict = {}

def enhance_for_eink(
    image_path,
    brightness_factor=1.15,
    contrast_factor=1.25,
    white_threshold=140
):
    print("=" * 60)
    print("ENHANCING IMAGE FOR E-INK")

    img = Image.open(image_path).convert("RGB")

    # Increase brightness
    img = ImageEnhance.Brightness(img).enhance(brightness_factor)

    # Increase contrast
    img = ImageEnhance.Contrast(img).enhance(contrast_factor)

    # Force near-white pixels to pure white
    pixels = img.load()
    width, height = img.size

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]

            if r >= white_threshold and g >= white_threshold and b >= white_threshold:
                pixels[x, y] = (255, 255, 255)

    img.save(image_path, format="BMP")

    print(f"Brightness : {brightness_factor}")
    print(f"Contrast   : {contrast_factor}")
    print(f"White Th.  : {white_threshold}")
    print("IMAGE ENHANCEMENT SUCCESS")
    print("=" * 60)


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


def render_sixcolorsmall():
    global today
    t_total_start = time.time()
    tmp_input_bmp = None
    tmp_output_bmp = None

    try:

        body = request.get_json(force=True, silent=True) or {}

        color_mode = (
            body.get("colorMode")
            or request.args.get("colorMode")
            or "SixColorSmall"
        )

        user_id = (
            body.get("userId")
            or request.args.get("userId")
            or "7FTK2"
        )

        print("=" * 60)
        print(f"USER ID      = {user_id}")
        print(f"COLOR MODE   = {color_mode}")

        # ============================================
        # CHECK CALENDAR + ALARM
        # ============================================

        alarm_doc = (
            db.collection("users")
            .document(user_id)
            .collection("modes")
            .document(color_mode)
            .get()
        )

        if not alarm_doc.exists:
            return jsonify({
                "error": "alarm document not found"
            }), 404

        alarm_data = alarm_doc.to_dict()

        # ============================================
        # CURRENT TIME
        # ============================================

        now = datetime.now(
            ZoneInfo("Asia/Kolkata")
        )

        today = now.strftime("%Y%m%d")

        now_minutes = (
                now.hour * 60 +
                now.minute
        )

        # ============================================
        # DEFAULT VALUES
        # ============================================

        active_alarm = None
        is_calendar = False

        # ============================================
        # 1. CHECK CALENDAR TIME FROM FIRESTORE
        # ============================================

        calendar_time = alarm_data.get("calendarTime")

        if calendar_time:

            try:

                calendar_dt = datetime.strptime(
                    calendar_time,
                    "%H:%M"
                )

                calendar_minutes = (
                        calendar_dt.hour * 60 +
                        calendar_dt.minute
                )

                calendar_diff = (
                        now_minutes - calendar_minutes
                )

                print("=" * 40)
                print("CHECKING CALENDAR")
                print(f"CURRENT TIME  = {now.strftime('%H:%M')}")
                print(f"CALENDAR TIME = {calendar_time}")
                print(f"DIFFERENCE    = {calendar_diff} min")

                # ========================================
                # 2-MINUTE CALENDAR WINDOW
                # ========================================

                if 0 <= calendar_diff <= 2:

                    calendar_path = (
                        f"users/{user_id}/images/"
                        f"{color_mode}/Frame/"
                        f"calendar/{today}.bmp"
                    )

                    calendar_blob = bucket.blob(
                        calendar_path
                    )

                    # ====================================
                    # CHECK CALENDAR IMAGE EXISTS
                    # ====================================

                    if calendar_blob.exists():

                        is_calendar = True

                        print(
                            f"CALENDAR MATCHED: "
                            f"date={today} "
                            f"time={calendar_time} "
                            f"diff={calendar_diff} min"
                        )

                        print(
                            f"CALENDAR IMAGE EXISTS: "
                            f"{calendar_path}"
                        )

                    else:

                        print(
                            f"CALENDAR IMAGE NOT FOUND: "
                            f"{calendar_path}"
                        )

                        print(
                            "CONTINUING TO CHECK ALARMS"
                        )

                else:

                    print("CALENDAR TIME NOT MATCHED")

            except Exception as e:

                print(
                    f"INVALID CALENDAR TIME: "
                    f"{calendar_time}"
                )

                print(f"ERROR = {e}")

        else:

            print("calendarTime NOT FOUND IN FIRESTORE")

        # ============================================
        # 2. CHECK ALARMS
        # Only check alarms when calendar is not active
        # ============================================

        if not is_calendar:

            print("=" * 40)
            print("CHECKING ALARMS")

            for alarm_name in [
                "alarm1",
                "alarm2",
                "alarm3"
            ]:

                alarm_time = alarm_data.get(
                    alarm_name
                )

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

                    diff = (
                            now_minutes - alarm_minutes
                    )

                    print(
                        f"CHECKING {alarm_name}: "
                        f"time={alarm_time}, "
                        f"diff={diff} min"
                    )

                    # ====================================
                    # 2-MINUTE ALARM WINDOW
                    # ====================================

                    if 0 <= diff <= 2:
                        active_alarm = alarm_name

                        print(
                            f"ALARM MATCHED: "
                            f"{alarm_name} "
                            f"time={alarm_time} "
                            f"diff={diff} min"
                        )

                        break

                except Exception as e:

                    print(
                        f"INVALID ALARM TIME: "
                        f"{alarm_name} = {alarm_time}"
                    )

                    print(f"ERROR = {e}")

        # ============================================
        # 3. SELECT IMAGE PATH
        #
        # PRIORITY:
        #
        # CALENDAR
        #    ↓
        # ALARM
        #    ↓
        # MANUAL
        #
        # ============================================

        if is_calendar:

            image_path = (
                f"users/{user_id}/images/"
                f"{color_mode}/Frame/"
                f"calendar/{today}.bmp"
            )

            output_type = "calendar"


        elif active_alarm:

            image_path = (
                f"users/{user_id}/images/"
                f"{color_mode}/Frame/"
                f"{active_alarm}/{today}.bmp"
            )

            output_type = "alarm"


        else:

            image_path = (
                f"users/{user_id}/images/"
                f"{color_mode}/Frame/"
                f"manual.bmp"
            )

            output_type = "manual"

        # ============================================
        # FINAL RESULT
        # ============================================

        print("=" * 60)

        print(
            f"CURRENT TIME = "
            f"{now.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        print(f"OUTPUT TYPE  = {output_type}")

        print(f"IMAGE PATH   = {image_path}")

        print("=" * 60)

        # ============================================
        # DOWNLOAD BMP
        # ============================================

        t0 = time.time()

        blob = bucket.blob(image_path)

        if not blob.exists():
            return jsonify({
                "error": "bmp image not found",
                "imagePath": image_path
            }), 404

        # ============================================
        # CREATE TEMP INPUT BMP
        # ============================================

        tmp_input_bmp = tempfile.NamedTemporaryFile(
            suffix=".bmp",
            delete=False
        )

        tmp_input_bmp.close()

        # ============================================
        # DOWNLOAD IMAGE FROM FIREBASE
        # ============================================

        blob.download_to_filename(
            tmp_input_bmp.name
        )

        print("IMAGE DOWNLOADED")

        # ============================================
        # CONVERT IMAGE TO RGB BMP
        # ============================================

        img = Image.open(
            tmp_input_bmp.name
        )

        img = img.convert("RGB")

        img.save(
            tmp_input_bmp.name,
            format="BMP"
        )

        enhance_for_eink(
            tmp_input_bmp.name,
            brightness_factor=1.15,
            contrast_factor=1.25,
            white_threshold=140
        )

        # ============================================
        # CALENDAR IMAGE PROCESSING
        # ONLY CALENDAR IMAGE
        # ============================================

        if output_type == "calendar":

            print("=" * 60)
            print("PROCESSING CALENDAR IMAGE")

            # ========================================
            # GET CITY FROM FIRESTORE
            # ========================================

            city = alarm_data.get("city")

            print(f"CITY FROM FIRESTORE = {city}")

            # ========================================
            # GET WEATHER + AQI BASED ON CITY
            # ========================================

            if city:

                weather_data = get_weather_data(
                    city
                )

            else:

                print("CITY NOT FOUND IN FIRESTORE")

                weather_data = {
                    "temperature": None,
                    "aqi": None
                }

            # ========================================
            # GET TEMPERATURE + AQI VALUES
            # ========================================

            temperature = weather_data.get(
                "temperature"
            )

            aqi = weather_data.get(
                "aqi"
            )

            # ========================================
            # TEMPERATURE TEXT
            # ========================================

            if temperature is None:

                temperature_text = "--°C"

            else:

                temperature_text = (
                    f"{round(temperature)}°C"
                )

            # ========================================
            # AQI TEXT
            # ========================================

            if aqi is None:

                aqi_text = "AQI --"

            else:

                aqi_text = (
                    f"AQI {round(aqi)}"
                )

            # ========================================
            # CREATE FINAL WEATHER TEXT
            # ========================================

            weather_text = (
                f"{temperature_text}   "
                f"{aqi_text}"
            )

            # ========================================
            # CREATE DATE + DAY TEXT
            # ========================================

            date_day_text = now.strftime(
                "%d %B %Y, %A"
            )

            # ========================================
            # DEBUG
            # ========================================

            print(f"DATE TEXT    = {date_day_text}")
            print(f"WEATHER TEXT = {weather_text}")

            # ========================================
            # ADD DATE + WEATHER TO CALENDAR IMAGE
            # ========================================

            add_calendar_overlay(
                tmp_input_bmp.name,
                date_day_text,
                weather_text
            )

            # ========================================
            # ROTATE CALENDAR IMAGE
            # 90 DEGREE ANTICLOCKWISE
            # ========================================

            img = Image.open(
                tmp_input_bmp.name
            ).convert("RGB")

            img = img.rotate(
                90,
                expand=True
            )

            img.save(
                tmp_input_bmp.name,
                format="BMP"
            )

            print(
                "CALENDAR IMAGE ROTATED "
                "90 DEGREE ANTICLOCKWISE"
            )

            print(
                "CALENDAR PROCESSING COMPLETED"
            )

            print("=" * 60)

        # ============================================
        # IMAGE DEBUG
        # ============================================

        img = Image.open(
            tmp_input_bmp.name
        )

        print("IMAGE PATH =", image_path)

        print(
            "LOCAL BMP =",
            tmp_input_bmp.name
        )

        print(
            "FILE SIZE =",
            os.path.getsize(
                tmp_input_bmp.name
            )
        )

        print(
            "MODE =",
            img.mode
        )

        print(
            "SIZE =",
            img.size
        )

        # ============================================
        # CREATE TEMP OUTPUT BMP
        # ============================================

        tmp_output_bmp = tempfile.NamedTemporaryFile(
            suffix=".bmp",
            delete=False
        )

        tmp_output_bmp.close()

        # ============================================
        # DOWNLOAD + PROCESSING TIME
        # ============================================

        t_bmp = (
                time.time() - t0
        )

        print("BMP DOWNLOAD = SUCCESS")

        print(
            f"[TIME] BMP DOWNLOAD + PROCESSING "
            f"= {t_bmp:.3f}s"
        )

        # ============================================
        # RENDER
        # ============================================

        t0 = time.time()

        cmd = [
            RENDER_BINARY,
            "-i", tmp_input_bmp.name,
            "-o", tmp_output_bmp.name,
            "-l", LUT_FILE,
            "-d", "1",
            "-m", "2"
        ]

        print(f"CMD = {' '.join(cmd)}")

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

        t_render = time.time() - t0

        print(f"[TIME] RENDER = {t_render:.3f}s")
        print(f"RETURN CODE = {result.returncode}")

        print("STDOUT =", result.stdout)
        print("STDERR =", result.stderr)

        if os.path.exists(tmp_output_bmp.name):
            print(
                "OUTPUT SIZE =",
                os.path.getsize(tmp_output_bmp.name)
            )

        if result.returncode != 0:
            return jsonify({
                "status": "render_failed",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }), 500

        print(f"OUTPUT FILE = {tmp_output_bmp.name}")
        print(f"INPUT FILE = {tmp_input_bmp.name}")

        if not os.path.exists(tmp_output_bmp.name):
            return jsonify({
                "status": "render_failed",
                "error": "output bmp not created"
            }), 500

        output_size = os.path.getsize(tmp_output_bmp.name)

        print(f"OUTPUT SIZE = {output_size}")

        if output_size == 0:
            return jsonify({
                "status": "render_failed",
                "error": "output bmp is empty"
            }), 500

        print("RENDER SUCCESS")

        # ============================================
        # BMP -> HEX
        # ============================================

        t0 = time.time()

        hex_string, width, height = render_to_hex(
            tmp_output_bmp.name
        )

        t_hex = time.time() - t0

        print(f"[TIME] HEX CONVERT = {t_hex:.3f}s")

        t0 = time.time()

        if is_calendar:

            txt_path = (
                f"users/{user_id}/"
                f"{color_mode}/"
                f"{color_mode}calendar.txt"
            )

            filename = f"{color_mode}calendar.txt"

        elif active_alarm:

            txt_path = (
                f"users/{user_id}/"
                f"{color_mode}/"
                f"{color_mode}alarm.txt"
            )

            filename = f"{color_mode}alarm.txt"

        else:

            txt_path = (
                f"users/{user_id}/"
                f"{color_mode}/"
                f"{color_mode}manual.txt"
            )

            filename = f"{color_mode}manual.txt"

        txt_blob = bucket.blob(txt_path)

        txt_blob.content_disposition = (
            f'attachment; filename="{filename}"'
        )

        txt_blob.upload_from_string(
            hex_string.encode("ascii"),
            content_type="application/octet-stream"
        )

        t_upload = time.time() - t0

        print(f"[TIME] UPLOAD = {t_upload:.3f}s")
        print(f"TXT PATH = {txt_path}")

        # ============================================
        # URLS
        # ============================================

        txt_url = (
            f"https://firebasestorage.googleapis.com/v0/b/"
            f"{bucket.name}/o/"
            f"{quote(txt_path, safe='')}"
            f"?alt=media"
        )

        txt_size = len(hex_string)

        t_total = time.time() - t_total_start

        print(f"[TIME] TOTAL = {t_total:.3f}s")
        print("=" * 60)

        return jsonify({
            "status": "success",

            # "type": "alarm" if active_alarm else "manual",
            "type": output_type,

            "txtUrl": txt_url,
            "txtPath": txt_path,

            "width": width,
            "height": height,

            "txtSize": txt_size,
            "hexLength": txt_size,

            "totalTimeSec": round(t_total, 3)
        })

    except subprocess.TimeoutExpired:

        print("[ERROR] Render timeout")

        return jsonify({
            "error": "render timeout after 60 seconds"
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
            except Exception:
                pass

        if len(_COLOR_CACHE) > 8192:
            _COLOR_CACHE.clear()



