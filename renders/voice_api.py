# import os
# import tempfile
#
# from flask import Flask, request, jsonify
# from flask_cors import CORS
# from sarvamai import SarvamAI
#
# app = Flask(__name__)
# CORS(app)
#
# # Keep the API key ONLY on the backend.
# SARVAM_API_KEY = os.environ.get("sk_cz0b6j2s_UWiXQtVbdO4O3Y6PNrJtghzm")
#
# if not SARVAM_API_KEY:
#     raise RuntimeError("SARVAM_API_KEY environment variable is not set")
#
# client = SarvamAI(
#     api_subscription_key=SARVAM_API_KEY
# )
#
#
# @app.route("/api/voice/transcribe", methods=["POST"])
# def transcribe_voice():
#
#     # ---------------------------------------------------------
#     # Check audio
#     # ---------------------------------------------------------
#     if "audio" not in request.files:
#         return jsonify({
#             "error": "No audio file received"
#         }), 400
#
#     audio = request.files["audio"]
#
#     if not audio.filename:
#         return jsonify({
#             "error": "Invalid audio file"
#         }), 400
#
#     temp_path = None
#
#     try:
#         # -----------------------------------------------------
#         # Save uploaded audio temporarily
#         # -----------------------------------------------------
#         extension = os.path.splitext(audio.filename)[1]
#
#         if not extension:
#             extension = ".webm"
#
#         with tempfile.NamedTemporaryFile(
#             delete=False,
#             suffix=extension
#         ) as temp_file:
#
#             audio.save(temp_file.name)
#             temp_path = temp_file.name
#
#         # -----------------------------------------------------
#         # Sarvam Speech-to-Text
#         #
#         # "unknown" = AUTOMATIC LANGUAGE DETECTION
#         # -----------------------------------------------------
#         with open(temp_path, "rb") as audio_file:
#
#             response = client.speech_to_text.transcribe(
#                 file=audio_file,
#                 model="saaras:v3",
#                 language_code="unknown",
#                 mode="transcribe"
#             )
#
#         # -----------------------------------------------------
#         # Get result
#         # -----------------------------------------------------
#         transcript = getattr(
#             response,
#             "transcript",
#             ""
#         ) or ""
#
#         detected_language = getattr(
#             response,
#             "language_code",
#             None
#         )
#
#         language_probability = getattr(
#             response,
#             "language_probability",
#             None
#         )
#
#         # -----------------------------------------------------
#         # Return to React
#         # -----------------------------------------------------
#         return jsonify({
#             "text": transcript.strip(),
#             "language": detected_language,
#             "language_probability": language_probability
#         })
#
#     except Exception as error:
#
#         print("================================")
#         print("VOICE TRANSCRIPTION ERROR")
#         print("================================")
#         print(error)
#
#         return jsonify({
#             "error": "Voice transcription failed",
#             "message": str(error)
#         }), 500
#
#     finally:
#
#         # -----------------------------------------------------
#         # Delete temporary audio file
#         # -----------------------------------------------------
#         if temp_path and os.path.exists(temp_path):
#
#             try:
#                 os.remove(temp_path)
#
#             except Exception:
#                 pass
#
#
# if __name__ == "__main__":
#
#     app.run(
#         host="0.0.0.0",
#         port=5000,
#         debug=False
#     )

import os
import tempfile

from flask import Blueprint, jsonify, request
from sarvamai import SarvamAI


voice_api = Blueprint("voice_api", __name__)

SARVAM_API_KEY = os.environ.get("sk_cz0b6j2s_UWiXQtVbdO4O3Y6PNrJtghzm")

if not SARVAM_API_KEY:
    raise RuntimeError(
        "SARVAM_API_KEY environment variable is not set"
    )

sarvam_client = SarvamAI(
    api_subscription_key=SARVAM_API_KEY
)


@voice_api.route(
    "/api/voice/transcribe",
    methods=["POST", "OPTIONS"]
)
def transcribe_voice():

    # CORS preflight
    if request.method == "OPTIONS":
        return "", 200

    if "audio" not in request.files:
        return jsonify({
            "success": False,
            "error": "No audio file received"
        }), 400

    audio = request.files["audio"]

    if not audio.filename:
        return jsonify({
            "success": False,
            "error": "Invalid audio file"
        }), 400

    temp_path = None

    try:

        # Get file extension from browser recording
        extension = os.path.splitext(
            audio.filename
        )[1]

        if not extension:
            extension = ".webm"

        # Save temporary audio
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extension
        ) as temp_file:

            audio.save(temp_file.name)
            temp_path = temp_file.name

        print(
            f"[VOICE] Received audio: "
            f"{audio.filename}"
        )

        # --------------------------------------------------
        # SARVAM SPEECH TO TEXT
        #
        # unknown = automatic language detection
        # --------------------------------------------------

        with open(temp_path, "rb") as audio_file:

            response = sarvam_client.speech_to_text.transcribe(
                file=audio_file,
                model="saaras:v3",
                language_code="unknown",
                mode="transcribe"
            )

        # --------------------------------------------------
        # Get transcript
        # --------------------------------------------------

        transcript = getattr(
            response,
            "transcript",
            ""
        ) or ""

        detected_language = getattr(
            response,
            "language_code",
            None
        )

        language_probability = getattr(
            response,
            "language_probability",
            None
        )

        transcript = transcript.strip()

        if not transcript:

            return jsonify({
                "success": False,
                "error": "No speech detected"
            }), 400

        print(
            f"[VOICE] Language: "
            f"{detected_language}"
        )

        print(
            f"[VOICE] Text: "
            f"{transcript}"
        )

        # --------------------------------------------------
        # Response expected by React
        # --------------------------------------------------

        return jsonify({
            "success": True,
            "text": transcript,
            "language": detected_language,
            "language_probability": language_probability
        })

    except Exception as e:

        print(
            "[VOICE] Transcription error:",
            str(e)
        )

        return jsonify({
            "success": False,
            "error": "Voice transcription failed",
            "message": str(e)
        }), 500

    finally:

        # Remove temporary audio
        if temp_path:

            try:

                if os.path.exists(temp_path):
                    os.remove(temp_path)

            except Exception as cleanup_error:

                print(
                    "[VOICE] Cleanup error:",
                    cleanup_error
                )