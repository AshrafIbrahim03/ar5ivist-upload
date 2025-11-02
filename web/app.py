import os
import subprocess
from flask import (
    Flask,
    flash,
    request,
    redirect,
    url_for,
    send_from_directory,
    jsonify,
    send_file,
)
from werkzeug.utils import secure_filename
from pathlib import Path
import random
import string

if os.environ.get("UPLOAD_FOLDER") is None:
    UPLOAD_FOLDER = Path.cwd() / "temp"
else:
    UPLOAD_FOLDER = Path(os.environ.get("UPLOAD_FOLDER"))

print(f"Using {UPLOAD_FOLDER.resolve()} as a temp upload directory...")
if not UPLOAD_FOLDER.exists():
    UPLOAD_FOLDER.mkdir()

TEMP_FILENAME_LEN = 10
ALLOWED_EXTS = {"tex"}

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def is_valid_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTS


@app.route("/", methods=["GET"])
def upload_page():
    return """
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    """


@app.route("/", methods=["POST"])
def upload_file():
    # Takes file, saves to random file name, runs docker container with it, then returns request with it
    if "file" not in request.files:
        flash("No file uploaded")
        return redirect(request.url)
    file = request.files["file"]
    if file.filename == "":
        flash("No file uploaded")
        return redirect(request.url)
    if file and is_valid_file(file.filename):
        filename = (
            "".join(
                random.choices(
                    string.ascii_letters + string.digits, k=TEMP_FILENAME_LEN
                )
            )
            + ".tex"
        )

        file.save(UPLOAD_FOLDER / filename)
        return redirect(url_for("download_file", name=filename))

    return """
    <!doctype html>
    <title>Upload new File</title>
    <h1>We couldn't handle your file</h1>
    """


@app.route("/uploads/<name>")
def download_file(name):
    return send_from_directory(UPLOAD_FOLDER, name)


@app.route("/process/<name>")
def process_file(name):
    if not (UPLOAD_FOLDER / name).exists():
        return """
    <!doctype html>
    <title>File does not exist</title>
    <h1>File does not exist</h1>
    """

    unprocessed_file = UPLOAD_FOLDER / name
    processed_file_path = UPLOAD_FOLDER / f"processed-{name.split('.')[0]}.html"
    cmd = [
        "docker",
        "exec",
        "ar5ivist",
        "latexmlc",
        "--preload=[nobibtex,rawstyles,nobreakuntex]latexml.sty",
        "--preload=ar5iv.sty",
        "--path=/opt/ar5iv-bindings/bindings",
        "--format=html5",
        "--pmml",
        "--mathtex",
        "--timeout=2700",
        f"--source={unprocessed_file.resolve()}",
        f"--dest={processed_file_path.resolve()}",
    ]
    result = subprocess.run(cmd, capture_output=True)

    if result.returncode != 0:
        return jsonify(
            {"error": "Conversion failed", "details": result.stderr.decode()}
        ), 500

    return send_file(processed_file_path, as_attachment=True, download_name=name)


if __name__ == "__main__":
    app.secret_key = "bruh"
    # "".join(
    # random.choices(string.ascii_letters + string.digits, k=TEMP_FILENAME_LEN)
    # )
    app.run()
