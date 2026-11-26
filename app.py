import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from sqlalchemy import text

from controllers.claim_controller import claim_bp
from controllers.ui_controller import ui_bp
from database import db
from middlewares.request_context import init_middleware


def create_app(test_config=None):
    load_dotenv()
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY") or os.urandom(32),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,
        UPLOAD_FOLDER=os.getenv(
            "UPLOAD_FOLDER",
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "uploads"),
        ),
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///claimaugment.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    db.init_app(app)

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"status": "error", "message": "Bad request."}), 400

    @app.errorhandler(404)
    def resource_not_found(error):
        return jsonify({"status": "error", "message": "Endpoint or resource not found."}), 404

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({"status": "error", "message": "File exceeds 16MB limit."}), 413

    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({"status": "error", "message": "Internal server error occurred."}), 500

    @app.route("/healthz", methods=["GET"])
    def health_check():
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "ok"}), 200

    init_middleware(app)
    app.register_blueprint(ui_bp)
    app.register_blueprint(claim_bp)

    with app.app_context():
        db.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5050))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    print(f"ClaimAugment AI backend starting on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
