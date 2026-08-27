from flask import request, jsonify
from firebase_admin import storage, firestore
from datetime import datetime, timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo

bucket = storage.bucket()
db = firestore.client()


def move_sixcolora3():

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

        # alarm1 = mode_data.get("alarm1")
        #
        # print(f"alarm1 = {alarm1}")
        #
        # if not alarm1:
        #
        #     return jsonify({
        #         "status": "error",
        #         "message": "alarm1 not configured"
        #     }), 400
        #
        #
        # # TIME CHECK
        # now = datetime.now(
        #     ZoneInfo("Asia/Kolkata")
        # )
        #
        # alarm_dt = datetime.strptime(
        #     alarm1,
        #     "%H:%M"
        # )
        #
        # alarm_dt = now.replace(
        #     hour=alarm_dt.hour,
        #     minute=alarm_dt.minute,
        #     second=0,
        #     microsecond=0
        # )
        #
        # window_end = alarm_dt + timedelta(minutes=2)
        #
        # # IMAGE SELECTION
        # if alarm_dt <= now <= window_end:
        #
        #     mode = "alarm"
        #
        #     today = now.strftime("%Y%m%d")
        #
        #     image_path = (
        #         f"users/{user_id}/images/"
        #         f"{color_mode}/Frame/{today}.bmp"
        #     )
        #
        # else:
        #
        #     mode = "manual"
        #
        #     image_path = (
        #         f"users/{user_id}/"
        #         f"{color_mode}/"
        #         f"sixColorA3.bmp"
        #     )

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
                f"sixColorA3.bmp"
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