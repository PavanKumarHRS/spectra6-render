import os

from PIL import Image, ImageDraw, ImageFont


# ============================================
# PATH CONFIG
# ============================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

FONT_PATH = os.path.join(
    BASE_DIR,
    "fonts",
    "Verdana-Bold.ttf"
)

print(f"FONT PATH = {FONT_PATH}")
print(f"FONT EXISTS = {os.path.exists(FONT_PATH)}")


# ============================================
# SETTINGS
# ============================================

TOP_BAND_HEIGHT = 120
BAND_OPACITY = 100

LEFT_MARGIN = 40
RIGHT_MARGIN = 40

DATE_FONT_SIZE = 55
WEATHER_FONT_SIZE = 45


def add_calendar_overlay(
        image_path,
        date_day_text,
        weather_text
):

    print("=" * 60)
    print("ADDING CALENDAR OVERLAY")

    # ============================================
    # CHECK FONT EXISTS
    # ============================================

    if not os.path.exists(FONT_PATH):

        raise FileNotFoundError(
            f"FONT FILE NOT FOUND: {FONT_PATH}"
        )


    # ============================================
    # OPEN IMAGE
    # ============================================

    img = Image.open(
        image_path
    ).convert("RGBA")

    canvas_width, canvas_height = img.size

    print(
        f"IMAGE SIZE = "
        f"{canvas_width} x {canvas_height}"
    )


    # ============================================
    # LOAD FONT
    # ============================================

    date_font = ImageFont.truetype(
        FONT_PATH,
        DATE_FONT_SIZE
    )

    weather_font = ImageFont.truetype(
        FONT_PATH,
        WEATHER_FONT_SIZE
    )


    # ============================================
    # CREATE TRANSPARENT OVERLAY
    # ============================================

    overlay = Image.new(
        "RGBA",
        img.size,
        (0, 0, 0, 0)
    )

    overlay_draw = ImageDraw.Draw(
        overlay
    )


    # ============================================
    # DRAW TOP RED BAND
    # ============================================

    overlay_draw.rectangle(
        (
            0,
            0,
            canvas_width,
            TOP_BAND_HEIGHT
        ),
        fill=(
            255,
            0,
            0,
            BAND_OPACITY
        )
    )


    # ============================================
    # COMBINE IMAGE + OVERLAY
    # ============================================

    img = Image.alpha_composite(
        img,
        overlay
    )

    draw = ImageDraw.Draw(img)


    # ============================================
    # DATE TEXT - LEFT
    # ============================================

    date_bbox = draw.textbbox(
        (0, 0),
        date_day_text,
        font=date_font
    )

    date_height = (
        date_bbox[3]
        - date_bbox[1]
    )

    date_y = (
        (TOP_BAND_HEIGHT - date_height) // 2
        - date_bbox[1]
    )

    draw.text(
        (
            LEFT_MARGIN,
            date_y
        ),
        date_day_text,
        fill="white",
        font=date_font
    )


    # ============================================
    # WEATHER TEXT - RIGHT
    # ============================================

    weather_bbox = draw.textbbox(
        (0, 0),
        weather_text,
        font=weather_font
    )

    weather_width = (
        weather_bbox[2]
        - weather_bbox[0]
    )

    weather_height = (
        weather_bbox[3]
        - weather_bbox[1]
    )

    weather_x = (
        canvas_width
        - weather_width
        - RIGHT_MARGIN
    )

    weather_y = (
        (TOP_BAND_HEIGHT - weather_height) // 2
        - weather_bbox[1]
    )

    draw.text(
        (
            weather_x,
            weather_y
        ),
        weather_text,
        fill="white",
        font=weather_font
    )


    # ============================================
    # SAVE RGB BMP
    # ============================================

    img = img.convert("RGB")

    img.save(
        image_path,
        format="BMP"
    )

    print("CALENDAR OVERLAY SUCCESS")
    print(f"DATE    = {date_day_text}")
    print(f"WEATHER = {weather_text}")
    print("=" * 60)