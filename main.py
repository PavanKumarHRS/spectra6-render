#deploy cmd
#gcloud builds submit --tag gcr.io/epaper-30f1b/spectra6-render

# gcloud run deploy spectra6-render \
#   --image gcr.io/epaper-30f1b/spectra6-render \
#   --region us-central1 \
#   --allow-unauthenticated



from flask import Flask, jsonify, request

from renders.sixcolor import render_sixcolor
from renders.sixcolora4 import render_sixcolora4
from renders.sixcolora2 import move_sixcolora2
from renders.sixcolora3 import move_sixcolora3
from renders.sixcolorsmall import render_sixcolorsmall
# from renders.fourcolor import render_fourcolor
from renders.local_render import render_local_bmp
from renders.mqtt_sender import send_to_device
from renders.voice_api import voice_api
from flask_cors import CORS

app = Flask(__name__)

CORS(
    app,
    resources={r"/*": {"origins": "*"}}
)

app.register_blueprint(voice_api)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "running_Spectra6"})

# @app.route("/renderFourColor", methods=["POST"])
# def fourcolor_route():
#     return render_fourcolor()

@app.route("/renderSixColor", methods=["POST"])
def sixcolor_route():
    return render_sixcolor()

@app.route("/renderSixColorA4", methods=["POST"])
def sixcolora4_route():
    return render_sixcolora4()

@app.route("/renderSixColorSmall", methods=["POST"])
def sixcolorsmall_route():
    return render_sixcolorsmall()

@app.route("/render", methods=["GET"])
def local_render_route():
    return render_local_bmp()


@app.route("/move_sixcolora2", methods=["POST"])
def move_sixcolora2_route():
    return move_sixcolora2()

@app.route("/move_sixcolora3", methods=["POST"])
def move_sixcolora3_route():
    return move_sixcolora3()

@app.route("/notifyDevice", methods=["POST", "OPTIONS"])
def notify_device():

    if request.method == "OPTIONS":
        return "", 200

    try:
        data = request.get_json()

        device_name = data.get("userId")

        if not device_name:
            return jsonify({
                "success": False,
                "message": "userId is required"
            }), 400

        send_to_device(device_name)

        return jsonify({
            "success": True,
            "device": device_name,
            "message": "Notification sent"
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False
    )
