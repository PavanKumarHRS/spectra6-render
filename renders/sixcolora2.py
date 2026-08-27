# from flask import request, jsonify
# from firebase_admin import storage
# from datetime import datetime
# from urllib.parse import quote
#
# bucket = storage.bucket()
#
# def move_sixcolora2():
#
#     try:
#
#         body = request.get_json(force=True) or {}
#
#         user_id = body.get("userId")
#         request_type = body.get("requestType")
#
#         if not user_id:
#             return jsonify({
#                 "status": "error",
#                 "message": "userId required"
#             }), 400
#
#         if not request_type:
#             return jsonify({
#                 "status": "error",
#                 "message": "requestType required"
#             }), 400
#
#         # ==========================================
#         # BUILD IMAGE PATH
#         # ==========================================
#
#         if request_type.lower() == "manual":
#
#             image_path = f"users/{user_id}/SixColorA2/sixColorA2.bmp"
#
#         elif request_type.lower() == "alarm":
#
#             today = datetime.now().strftime("%Y%m%d")
#
#             image_path = (
#                 f"users/{user_id}/images/"
#                 f"SixColorA2/Frame/{today}.bmp"
#             )
#
#         else:
#
#             return jsonify({
#                 "status": "error",
#                 "message": "requestType must be alarm or manual"
#             }), 400
#
#         # ==========================================
#         # CHECK FILE EXISTS
#         # ==========================================
#
#         blob = bucket.blob(image_path)
#
#         if not blob.exists():
#
#             return jsonify({
#                 "status": "error",
#                 "message": "Image not found",
#                 "imagePath": image_path
#             }), 404
#
#         # ==========================================
#         # RETURN URL
#         # ==========================================
#
#         # image_url = blob.public_url
#
#         encoded_path = quote(image_path, safe="")
#
#         image_url = (
#             f"https://firebasestorage.googleapis.com/v0/b/"
#             f"epaper-30f1b.firebasestorage.app/o/"
#             f"{encoded_path}?alt=media"
#         )
#
#         return jsonify({
#             "status": "success",
#             "requestType": request_type,
#             "imagePath": image_path,
#             "imageUrl": image_url
#         }), 200
#
#     except Exception as e:
#
#         return jsonify({
#             "status": "error",
#             "message": str(e)
#         }), 500


from flask import request, jsonify
from firebase_admin import storage, firestore
from datetime import datetime, timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo

bucket = storage.bucket()
db = firestore.client()


def move_sixcolora2():

    try:

        body = request.get_json(force=True) or {}

        user_id = body.get("userId")
        color_mode = body.get("colorMode")

        if not user_id:
            return jsonify({
                "status": "error",
                "message": "userId required"
            }), 400

        if not color_mode:
            return jsonify({
                "status": "error",
                "message": "colorMode required"
            }), 400

        # READ USER DOCUMENT
        mode_doc = (
            db.collection("users")
            .document(user_id)
            .collection("modes")
            .document(color_mode)
            .get()
        )

        if not mode_doc.exists:
            return jsonify({
                "status": "error",
                "message": f"Mode document not found: {color_mode}"
            }), 404

        mode_data = mode_doc.to_dict()

        # CURRENT TIME
        now = datetime.now(
            ZoneInfo("Asia/Kolkata")
        )

        active_alarm = None
        active_alarm_time = None

        # CHECK ALL ALARMS
        for alarm_name in ["alarm1", "alarm2", "alarm3"]:

            alarm_time = mode_data.get(alarm_name)

            print(f"{alarm_name} = {alarm_time}")

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
                    active_alarm_time = alarm_time

                    print(
                        f"ALARM MATCHED: "
                        f"{alarm_name} "
                        f"time={alarm_time} "
                        f"diff={diff}"
                    )

                    break

            except Exception as e:

                print(
                    f"Invalid alarm time "
                    f"{alarm_name}: {alarm_time}"
                )

        # IMAGE SELECTION
        if active_alarm:

            mode = "alarm"

            today = now.strftime("%Y%m%d")

            image_path = (
                f"users/{user_id}/images/"
                f"{color_mode}/Frame/{active_alarm}/{today}.bmp"
            )

        else:

            mode = "manual"

            image_path = (
                f"users/{user_id}/images/"
                f"{color_mode}/Frame/"
                f"sixColorA2.bmp"
            )


        # CHECK IMAGE EXISTS
        blob = bucket.blob(image_path)

        if not blob.exists():

            return jsonify({
                "status": "error",
                "message": "Image not found",
                "mode": mode,
                "imagePath": image_path
            }), 404

        # GENERATE DOWNLOAD URL
        encoded_path = quote(
            image_path,
            safe=""
        )

        image_url = (
            "https://firebasestorage.googleapis.com/v0/b/"
            "epaper-30f1b.firebasestorage.app/o/"
            f"{encoded_path}?alt=media"
        )

        return jsonify({
            "status": "success",
            "mode": mode,
            "activeAlarm": active_alarm,
            "alarmTime": active_alarm_time,
            "currentTime": now.strftime("%H:%M:%S"),
            "imagePath": image_path,
            "imageUrl": image_url
        }), 200

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500