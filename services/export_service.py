import io
import json
import os
import zipfile


class ExportService:
    @staticmethod
    def generate_claim_zip(payload, upload_folder):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for image in payload["images"]:
                image_url = image.get("url", "")
                filename = os.path.basename(image_url)
                if not filename:
                    continue
                file_path = os.path.join(upload_folder, filename)
                if os.path.isfile(file_path):
                    archive.write(file_path, arcname=f"dataset/{filename}")

            report = json.dumps(payload, indent=2)
            archive.writestr("claim_report.json", report)
            archive.writestr(
                "dataset/ai_assessment_manifest.json",
                json.dumps(payload.get("ai_assessment", {}), indent=2),
            )

        zip_buffer.seek(0)
        return zip_buffer
