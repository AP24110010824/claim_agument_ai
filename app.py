import os
import uuid
import json
import io
import zipfile
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, send_from_directory, send_file
from werkzeug.utils import secure_filename

# Import our verified core modules
from modules.augmenter import augment_claim_image
from modules.classifier import classify_damage_description

# Load environment variables (.env)
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# =====================================================================
# PRODUCTION CONFIGURATION
# =====================================================================
# 1. DoS Protection: Limit maximum upload size to 16 Megabytes
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

# 2. Upload storage directory
UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 3. Whitelisted image extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def is_allowed_file(filename: str) -> bool:
    """
    Security check: Validates that the file has an extension
    and that the extension is strictly in our image whitelist.
    """
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# =====================================================================
# CENTRALIZED ERROR HANDLERS (Fault Tolerance)
# =====================================================================
@app.errorhandler(413)
def request_entity_too_large(error):
    """Triggered automatically when uploaded file exceeds 16MB."""
    return jsonify({
        "status": "error",
        "message": "File exceeds maximum upload limit of 16MB."
    }), 413

@app.errorhandler(404)
def resource_not_found(error):
    return jsonify({
        "status": "error",
        "message": "The requested endpoint or resource was not found."
    }), 404

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({
        "status": "error",
        "message": "An internal server error occurred. Please try again."
    }), 500

# =====================================================================
# ROUTES
# =====================================================================
@app.route("/", methods=["GET"])
def index():
    """Renders the Liquid Glass Actuarial Cockpit."""
    try:
        return render_template("index.html")
    except Exception as e:
        return jsonify({
            "service": "ClaimAugment AI",
            "version": "1.0.0",
            "status": "healthy",
            "error": str(e)
        })

@app.route("/uploads/<path:filename>", methods=["GET"])
def serve_upload(filename):
    """
    Secure file delivery: send_from_directory prevents directory traversal
    attacks (e.g. requests with ../../)
    """
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/api/process-claim", methods=["POST"])
def process_claim():
    """
    Main orchestration endpoint:
    1. Validates and saves the uploaded photo securely.
    2. Runs the 5-point Computer Vision augmentation pipeline.
    3. Runs the Groq LLM damage classification.
    4. Returns a unified JSON response.
    """
    # 1. Validation: Verify file was sent
    if "photo" not in request.files:
        return jsonify({"status": "error", "message": "No 'photo' field in form-data."}), 400

    file = request.files["photo"]
    if file.filename == "":
        return jsonify({"status": "error", "message": "No file selected."}), 400

    if not is_allowed_file(file.filename):
        return jsonify({
            "status": "error",
            "message": f"Invalid file type. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}"
        }), 400

    # 2. Sanitize filename & prevent collisions using UUID
    original_clean_name = secure_filename(file.filename)
    unique_prefix = uuid.uuid4().hex[:8]
    unique_filename = f"{unique_prefix}_{original_clean_name}"
    saved_input_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)

    # Save to disk
    file.save(saved_input_path)

    # 3. Extract claims notes
    notes = request.form.get("notes", "").strip()

    try:
        # 4. Orchestration Step A: Run Augmentation Pipeline (OpenCV + Albumentations)
        raw_augmented_results = augment_claim_image(saved_input_path, app.config["UPLOAD_FOLDER"])
        
        # Build browser-accessible URLs for augmented images
        augmented_files = [
            {
                "effect": item["effect"],
                "filename": item["filename"],
                "url": f"/uploads/{item['filename']}"
            }
            for item in raw_augmented_results
        ]

        # 5. Orchestration Step B: Run AI Damage Classification (Groq LLM)
        ai_assessment = classify_damage_description(notes)

        # 6. Return unified production response
        return jsonify({
            "status": "success",
            "data": {
                "original_image": {
                    "filename": unique_filename,
                    "url": f"/uploads/{unique_filename}"
                },
                "augmented_images": augmented_files,
                "ai_assessment": ai_assessment
            }
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Processing failed: {str(e)}"
        }), 500

@app.route("/api/export-zip", methods=["POST"])
def export_zip():
    """
    Bundles the original photo, all 5 augmented photos, and an AI metadata manifest
    into an in-memory ZIP archive for instant 1-click download.
    """
    data = request.get_json()
    if not data or "images" not in data:
        return jsonify({"status": "error", "message": "No images provided"}), 400

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # 1. Add images
        for img in data["images"]:
            filename = os.path.basename(img["url"])
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            if os.path.exists(file_path):
                zip_file.write(file_path, arcname=f"dataset/{filename}")

        # 2. Add AI assessment manifest
        manifest_content = json.dumps(data.get("ai_assessment", {}), indent=2)
        zip_file.writestr("dataset/ai_assessment_manifest.json", manifest_content)

    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name="ClaimAugment_Synthetic_Dataset.zip"
    )

# =====================================================================
# APPLICATION ENTRYPOINT
# =====================================================================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5050))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    print(f"🚀 ClaimAugment AI backend starting on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)