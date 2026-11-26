from flask import Blueprint, current_app, jsonify, request, send_file

from modules.classifier import DamageClassificationError
from services.claim_service import ClaimService
from services.export_service import ExportService


claim_bp = Blueprint("claim_bp", __name__, url_prefix="/api")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def is_allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@claim_bp.route("/process-claim", methods=["POST"])
def process_claim():
    if "photo" in request.files:
        uploaded_file = request.files["photo"]
    elif "file" in request.files:
        uploaded_file = request.files["file"]
    else:
        return jsonify({"status": "error", "message": "No 'photo' field in form-data."}), 400

    if uploaded_file.filename == "":
        return jsonify({"status": "error", "message": "No file selected."}), 400

    if not is_allowed_file(uploaded_file.filename):
        return jsonify({
            "status": "error",
            "message": f"Invalid format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        }), 400

    try:
        payload = ClaimService.process_claim(
            uploaded_file,
            request.form.get("notes", "").strip(),
            request.form.get("vehicle_type", "").strip(),
            current_app.config["UPLOAD_FOLDER"],
            request.form.get("preset", "").strip(),
        )
        return jsonify(payload), 200
    except DamageClassificationError as error:
        return jsonify({"status": "error", "message": str(error)}), error.status_code
    except Exception as error:
        return jsonify({"status": "error", "message": f"Processing failed: {error}"}), 500


@claim_bp.route("/export-zip", methods=["POST"])
def export_zip():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or "images" not in payload or not isinstance(payload["images"], list):
        return jsonify({"status": "error", "message": "No images provided"}), 400

    zip_buffer = ExportService.generate_claim_zip(payload, current_app.config["UPLOAD_FOLDER"])
    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name="ClaimAugment_Synthetic_Dataset.zip",
    )


@claim_bp.route("/claims", methods=["GET"])
def list_claims():
    claims = ClaimService.list_claims()
    return jsonify({"status": "success", "count": len(claims), "data": claims}), 200


@claim_bp.route("/claims/<claim_id>", methods=["GET"])
def get_claim(claim_id):
    claim = ClaimService.get_claim_by_id(claim_id)
    if claim is None:
        return jsonify({"status": "error", "message": "Claim not found."}), 404
    return jsonify({"status": "success", "data": claim}), 200
