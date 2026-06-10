#deploy cmd
#gcloud builds submit --tag gcr.io/epaper-30f1b/spectra6-render

# gcloud run deploy spectra6-render \
#   --image gcr.io/epaper-30f1b/spectra6-render \
#   --region us-central1 \
#   --allow-unauthenticated

from flask import Flask, jsonify

from renders.sixcolor import render_sixcolor
from renders.sixcolora4 import render_sixcolora4
from renders.sixcolora2 import move_sixcolora2
from renders.sixcolora3 import move_sixcolora3

app = Flask(__name__)


@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "running_Spectra6"})


@app.route("/renderSixColor", methods=["POST"])
def sixcolor_route():
    return render_sixcolor()


@app.route("/renderSixColorA4", methods=["POST"])
def sixcolora4_route():
    return render_sixcolora4()

@app.route("/move_sixcolora2", methods=["POST"])
def move_sixcolora2_route():
    return move_sixcolora2()

@app.route("/move_sixcolora3", methods=["POST"])
def move_sixcolora3_route():
    return move_sixcolora3()


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False
    )
