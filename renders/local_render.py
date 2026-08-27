from flask import send_file, jsonify
from PIL import Image

import subprocess
import os


# =====================================================
# CONFIG
# =====================================================

INPUT_BMP = "./input.bmp"

OUTPUT_BMP = "/tmp/rendered_output.bmp"
OUTPUT_TXT = "/tmp/image_sq_768x552.txt"

WIDTH = 768
HEIGHT = 552


# =====================================================
# SPECTRA6 SDK
# =====================================================

RENDER_BINARY = "./render_sdk/Spectra6_render_x86_64"

LUT_FILE = (
    "./render_sdk/bin/"
    "Spectra6_Render_LUT_6color_Default_v1.bin"
)

LIB_PATH = "./render_sdk/lib"


# =====================================================
# COLOR CODES - 4 BIT
# =====================================================

COLOR_BLACK = 0x0
COLOR_WHITE = 0x1
COLOR_GREEN = 0x6
COLOR_BLUE = 0x5
COLOR_RED = 0x3
COLOR_YELLOW = 0x2


# =====================================================
# COLOR PALETTE
# =====================================================

palette = [
    ((0, 0, 0), COLOR_BLACK),
    ((255, 255, 255), COLOR_WHITE),
    ((0, 255, 0), COLOR_GREEN),
    ((0, 0, 255), COLOR_BLUE),
    ((255, 0, 0), COLOR_RED),
    ((255, 255, 0), COLOR_YELLOW),
]


# =====================================================
# FIND NEAREST COLOR
# =====================================================

def nearest_color(r, g, b):

    best = COLOR_WHITE
    best_dist = 1e9

    for (pr, pg, pb), idx in palette:

        d = (
            (r - pr) ** 2
            + (g - pg) ** 2
            + (b - pb) ** 2
        )

        if d < best_dist:
            best_dist = d
            best = idx

    return best


# =====================================================
# RENDERED BMP -> RAW 4BPP DATA
#
# 2 PIXELS = 1 BYTE
#
# Example:
#
# Red    = 3
# Yellow = 2
#
# (3 << 4) | 2
# = 0x32
#
# We store actual byte 0x32.
# NOT string "32"
# NOT string "0x32"
# =====================================================

def rendered_bmp_to_bytes(rendered_bmp_path):

    print("=" * 60)
    print("RENDERED BMP -> RAW 4BPP")
    print("=" * 60)

    img = Image.open(
        rendered_bmp_path
    ).convert("RGB")

    print(
        "RENDERED SIZE =",
        img.size
    )

    print(
        "RENDERED MODE =",
        img.mode
    )


    # =================================================
    # SIZE CHECK
    # =================================================

    if img.size != (WIDTH, HEIGHT):

        print(
            "RESIZING:",
            img.size,
            "->",
            (WIDTH, HEIGHT)
        )

        img = img.resize(
            (WIDTH, HEIGHT)
        )


    pixels = img.load()

    image_data = bytearray()


    # =================================================
    # 2 PIXELS -> 1 BYTE
    # =================================================

    for y in range(HEIGHT):

        for x in range(0, WIDTH, 2):

            # Pixel 1
            c1 = nearest_color(
                *pixels[x, y]
            )

            # Pixel 2
            c2 = nearest_color(
                *pixels[x + 1, y]
            )


            # =========================================
            # PACK TWO 4-BIT VALUES
            #
            # c1 = HIGH nibble
            # c2 = LOW nibble
            # =========================================

            value = (
                (c1 << 4)
                | c2
            )


            # =========================================
            # STORE ACTUAL BYTE
            # =========================================

            image_data.append(
                value
            )


    img.close()


    # =================================================
    # SIZE CHECK
    # =================================================

    expected_bytes = (
        WIDTH * HEIGHT
    ) // 2


    print(
        "IMAGE DATA BYTES =",
        len(image_data)
    )

    print(
        "EXPECTED BYTES =",
        expected_bytes
    )


    if len(image_data) != expected_bytes:

        raise RuntimeError(
            "Image byte count mismatch"
        )


    print(
        "IMAGE BYTE CHECK = OK"
    )


    return image_data


# =====================================================
# MAIN RENDER FUNCTION
# =====================================================

def render_local_bmp():

    try:

        print("\n")
        print("=" * 60)
        print("SPECTRA6 RENDER START")
        print("=" * 60)


        # =================================================
        # CHECK INPUT
        # =================================================

        if not os.path.exists(INPUT_BMP):

            return jsonify({
                "error": "input.bmp not found",
                "path": INPUT_BMP
            }), 404


        # =================================================
        # CHECK RENDERER
        # =================================================

        if not os.path.exists(RENDER_BINARY):

            return jsonify({
                "error": "renderer not found",
                "path": RENDER_BINARY
            }), 500


        # =================================================
        # CHECK LUT
        # =================================================

        if not os.path.exists(LUT_FILE):

            return jsonify({
                "error": "LUT not found",
                "path": LUT_FILE
            }), 500


        # =================================================
        # EXECUTE PERMISSION
        # =================================================

        os.chmod(
            RENDER_BINARY,
            0o755
        )


        # =================================================
        # INPUT INFO
        # =================================================

        input_img = Image.open(
            INPUT_BMP
        )


        print(
            "INPUT SIZE =",
            input_img.size
        )

        print(
            "INPUT MODE =",
            input_img.mode
        )


        input_img.close()


        # =================================================
        # DELETE OLD OUTPUT
        # =================================================

        if os.path.exists(OUTPUT_BMP):
            os.remove(OUTPUT_BMP)

        if os.path.exists(OUTPUT_TXT):
            os.remove(OUTPUT_TXT)


        # =================================================
        # SPECTRA6 COMMAND
        # =================================================

        cmd = [
            RENDER_BINARY,

            "-i",
            INPUT_BMP,

            "-o",
            OUTPUT_BMP,

            "-l",
            LUT_FILE,

            "-d",
            "1",

            "-m",
            "2"
        ]


        print("=" * 60)
        print("RUNNING SPECTRA6")
        print("=" * 60)

        print(
            "COMMAND =",
            " ".join(cmd)
        )


        # =================================================
        # LIBRARY PATH
        # =================================================

        env = os.environ.copy()

        env["LD_LIBRARY_PATH"] = (
            os.path.abspath(
                LIB_PATH
            )
        )


        # =================================================
        # RUN SPECTRA6
        # =================================================

        result = subprocess.run(
            cmd,

            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,

            text=True,

            env=env,

            timeout=60
        )


        print(
            "RETURN CODE =",
            result.returncode
        )


        if result.stdout:

            print(
                "STDOUT =",
                result.stdout
            )


        if result.stderr:

            print(
                "STDERR =",
                result.stderr
            )


        # =================================================
        # CHECK RENDER RESULT
        # =================================================

        if result.returncode != 0:

            return jsonify({
                "error":
                    "Spectra6 render failed",

                "returnCode":
                    result.returncode,

                "stdout":
                    result.stdout,

                "stderr":
                    result.stderr
            }), 500


        # =================================================
        # CHECK OUTPUT BMP
        # =================================================

        if not os.path.exists(
            OUTPUT_BMP
        ):

            return jsonify({
                "error":
                    "rendered_output.bmp not created"
            }), 500


        bmp_file_size = os.path.getsize(
            OUTPUT_BMP
        )


        if bmp_file_size == 0:

            return jsonify({
                "error":
                    "rendered_output.bmp is empty"
            }), 500


        # =================================================
        # RENDERED BMP INFO
        # =================================================

        rendered_img = Image.open(
            OUTPUT_BMP
        )


        print("=" * 60)
        print("SPECTRA6 RENDER SUCCESS")
        print("=" * 60)


        print(
            "OUTPUT BMP =",
            OUTPUT_BMP
        )

        print(
            "OUTPUT SIZE =",
            rendered_img.size
        )

        print(
            "OUTPUT MODE =",
            rendered_img.mode
        )

        print(
            "BMP FILE SIZE =",
            bmp_file_size
        )


        rendered_img.close()


        # =================================================
        # RENDERED BMP -> RAW 4BPP
        # =================================================

        image_data = rendered_bmp_to_bytes(
            OUTPUT_BMP
        )


        # =================================================
        # HEADER
        #
        # ASCII = start#
        #
        # HEX:
        #
        # 73 74 61 72 74 23
        #
        # 6 BYTES
        # =================================================

        header = bytes([
            0x73,
            0x74,
            0x61,
            0x72,
            0x74,
            0x23
        ])


        # =================================================
        # FOOTER
        #
        # ASCII = #end
        #
        # HEX:
        #
        # 23 65 6E 64
        #
        # 4 BYTES
        # =================================================

        footer = bytes([
            0x23,
            0x65,
            0x6E,
            0x64
        ])


        # =================================================
        # FINAL RAW DATA
        #
        # HEADER
        # +
        # IMAGE 1
        # +
        # IMAGE 2
        # +
        # FOOTER
        # =================================================

        final_data = (
            header
            + bytes(image_data)
            + bytes(image_data)
            + footer
        )


        # =================================================
        # SIZE INFORMATION
        # =================================================

        image_bytes = len(
            image_data
        )


        final_bytes = len(
            final_data
        )


        expected_image_bytes = (
            WIDTH * HEIGHT
        ) // 2


        expected_final_bytes = (
            len(header)
            + expected_image_bytes
            + expected_image_bytes
            + len(footer)
        )


        print("=" * 60)
        print("FINAL DATA INFORMATION")
        print("=" * 60)


        print(
            "HEADER BYTES =",
            len(header)
        )


        print(
            "IMAGE 1 BYTES =",
            image_bytes
        )


        print(
            "IMAGE 2 BYTES =",
            image_bytes
        )


        print(
            "FOOTER BYTES =",
            len(footer)
        )


        print(
            "FINAL DATA BYTES =",
            final_bytes
        )


        print(
            "EXPECTED FINAL BYTES =",
            expected_final_bytes
        )


        # =================================================
        # CHECK
        # =================================================

        if final_bytes != expected_final_bytes:

            raise RuntimeError(
                "Final data byte count mismatch"
            )


        print(
            "FINAL BYTE CHECK = OK"
        )


        # =================================================
        # SAVE RAW DATA
        #
        # IMPORTANT:
        #
        # "wb" = binary write
        #
        # This stores actual bytes.
        #
        # File size will be 423946 bytes.
        # =================================================

        with open(
            OUTPUT_TXT,
            "wb"
        ) as f:

            f.write(
                final_data
            )


        # =================================================
        # VERIFY SAVED FILE
        # =================================================

        saved_file_size = os.path.getsize(
            OUTPUT_TXT
        )


        print("=" * 60)
        print("RAW FILE CREATED")
        print("=" * 60)


        print(
            "FILE PATH =",
            OUTPUT_TXT
        )


        print(
            "FINAL DATA BYTES =",
            final_bytes
        )


        print(
            "SAVED FILE SIZE =",
            saved_file_size
        )


        print(
            "EXPECTED FILE SIZE =",
            expected_final_bytes
        )


        if saved_file_size != expected_final_bytes:

            raise RuntimeError(
                "Saved file size mismatch"
            )


        print(
            "FILE SIZE CHECK = OK"
        )


        print("=" * 60)
        print("PROCESS COMPLETE")
        print("=" * 60)


        # =================================================
        # RETURN RAW FILE
        # =================================================

        return send_file(
            OUTPUT_TXT,

            mimetype="application/octet-stream",

            as_attachment=True,

            download_name=
                "image_sq_768x552.txt"
        )


    # =====================================================
    # TIMEOUT
    # =====================================================

    except subprocess.TimeoutExpired:

        return jsonify({
            "error":
                "Spectra6 render timeout after 60 seconds"
        }), 500


    # =====================================================
    # OTHER ERROR
    # =====================================================

    except Exception as e:

        print(
            "ERROR =",
            str(e)
        )


        return jsonify({
            "error":
                str(e)
        }), 500