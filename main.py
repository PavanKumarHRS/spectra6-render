# from fastapi import FastAPI
# from fastapi import Request
#
# import firebase_admin
# from firebase_admin import credentials
# from firebase_admin import storage
#
# from PIL import Image
#
# import subprocess
# import os
#
# app = FastAPI()
#
# cred = credentials.Certificate(
#     "firebase/serviceAccount.json"
# )
#
# firebase_admin.initialize_app(cred, {
#     'storageBucket':'epaper-30f1b.firebasestorage.app'
# })
#
# bucket = storage.bucket()
#
#
# @app.get("/")
# def home():
#     return {
#         "status": "running"
#     }
#
#
# @app.post("/render")
# async def render(req: Request):
#
#     try:
#         data = await req.json()
#
#         image_path = data["imagePath"]
#
#         # ----------------------------
#         # TEMP FILES
#         # ----------------------------
#
#         local_png = "/tmp/input.png"
#         local_bmp = "/tmp/input.bmp"
#         local_output_bmp = "/tmp/output.bmp"
#         local_output_txt = "/tmp/SixColoralarm.txt"
#
#         # ----------------------------
#         # DOWNLOAD PNG FROM FIREBASE
#         # ----------------------------
#
#         blob = bucket.blob(image_path)
#
#         blob.download_to_filename(local_png)
#
#         print("PNG Downloaded")
#
#         # ----------------------------
#         # CONVERT PNG → BMP
#         # ----------------------------
#
#         image = Image.open(local_png)
#
#         image = image.convert("RGB")
#
#         image.save(local_bmp)
#
#         print("BMP Created")
#
#         # ----------------------------
#         # LUT FILE
#         # ----------------------------
#
#         lut_file = (
#             "./render_sdk/bin/"
#             "Spectra6_Render_LUT_6color_Default_v1.bin"
#         )
#
#         # ----------------------------
#         # RUN SPECTRA6 RENDERER
#         # ----------------------------
#
#         cmd = [
#             "./render_sdk/Spectra6_render_x86_64",
#             local_bmp,
#             local_output_bmp,
#             lut_file
#         ]
#
#         result = subprocess.run(
#             cmd,
#             capture_output=True,
#             text=True
#         )
#
#         print(result.stdout)
#         print(result.stderr)
#
#         # ----------------------------
#         # VERIFY OUTPUT BMP EXISTS
#         # ----------------------------
#
#         if not os.path.exists(local_output_bmp):
#             return {
#                 "status": "render_failed",
#                 "stderr": result.stderr
#             }
#
#         print("Render Success")
#
#         # ----------------------------
#         # BMP → HEX/TXT
#         # ----------------------------
#
#         with open(local_output_bmp, "rb") as bmp_file:
#             bmp_bytes = bmp_file.read()
#
#         hex_string = bmp_bytes.hex()
#
#         with open(local_output_txt, "w") as txt_file:
#             txt_file.write(hex_string)
#
#         print("TXT Generated")
#
#         # ----------------------------
#         # UPLOAD TXT TO FIREBASE
#         # ----------------------------
#
#         output_blob = bucket.blob(
#             "users/7FTK2/SixColor/SixColoralarm.txt"
#         )
#
#         output_blob.upload_from_filename(
#             local_output_txt,
#             content_type="text/plain"
#         )
#
#         print("TXT Uploaded")
#
#         return {
#             "status": "success",
#             "txtPath": "users/7FTK2/SixColor/SixColoralarm.txt"
#         }
#
#     except Exception as e:
#
#         return {
#             "status": "error",
#             "message": str(e)
#         }


from flask import Flask, jsonify

from renders.sixcolor import render_sixcolor
from renders.sixcolora4 import render_sixcolora4

app = Flask(__name__)


@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "running"})


@app.route("/renderSixColor", methods=["POST"])
def sixcolor_route():
    return render_sixcolor()


@app.route("/renderSixColorA4", methods=["POST"])
def sixcolora4_route():
    return render_sixcolora4()


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False
    )