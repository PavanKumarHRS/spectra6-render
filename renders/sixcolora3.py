from flask import request, jsonify
from firebase_admin import storage
from datetime import datetime
from urllib.parse import quote

bucket = storage.bucket()

def move_sixcolora3():

    try:

        body = request.get_json(force=True) or {}

        user_id = body.get("userId")
        request_type = body.get("requestType")

        if not user_id:
            return jsonify({
                "status": "error",
                "message": "userId required"
            }), 400

        if not request_type:
            return jsonify({
                "status": "error",
                "message": "requestType required"
            }), 400

        # ==========================================
        # BUILD IMAGE PATH
        # ==========================================

        if request_type.lower() == "manual":

            image_path = f"users/{user_id}/SixColorA3/sixColorA3.bmp"

        elif request_type.lower() == "alarm":

            today = datetime.now().strftime("%Y%m%d")

            image_path = (
                f"users/{user_id}/images/"
                f"SixColorA3/Frame/{today}.bmp"
            )

        else:

            return jsonify({
                "status": "error",
                "message": "requestType must be alarm or manual"
            }), 400

        # ==========================================
        # CHECK FILE EXISTS
        # ==========================================

        blob = bucket.blob(image_path)

        if not blob.exists():

            return jsonify({
                "status": "error",
                "message": "Image not found",
                "imagePath": image_path
            }), 404

        # ==========================================
        # RETURN URL
        # ==========================================

        # image_url = blob.public_url

        encoded_path = quote(image_path, safe="")

        image_url = (
            f"https://firebasestorage.googleapis.com/v0/b/"
            f"epaper-30f1b.firebasestorage.app/o/"
            f"{encoded_path}?alt=media"
        )

        return jsonify({
            "status": "success",
            "requestType": request_type,
            "imagePath": image_path,
            "imageUrl": image_url
        }), 200

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500