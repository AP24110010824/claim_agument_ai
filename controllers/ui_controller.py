from flask import Blueprint, current_app, render_template, send_from_directory


ui_bp = Blueprint("ui_bp", __name__)


@ui_bp.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@ui_bp.route("/uploads/<path:filename>", methods=["GET"])
def serve_upload(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
