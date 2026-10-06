import json
import os
import threading
import time

from flask import Flask, Response, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

from transcoder import Transcoder

app = Flask(__name__)

INPUT_DIR = os.environ.get("INPUT_DIR", "/inputs")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/outputs")

max_gb = int(os.environ.get("MAX_UPLOAD_SIZE_GB", "10"))
app.config["MAX_CONTENT_LENGTH"] = max_gb * 1024 * 1024 * 1024

transcoder = Transcoder()


def _safe_path(directory, filename):
    filepath = os.path.realpath(os.path.join(directory, filename))
    if not filepath.startswith(os.path.realpath(directory) + os.sep):
        raise ValueError("Ruta de archivo no válida")
    return filepath


def _format_size(size_bytes):
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/files")
def list_files():
    files = []
    if os.path.exists(INPUT_DIR):
        for name in sorted(os.listdir(INPUT_DIR)):
            filepath = os.path.join(INPUT_DIR, name)
            if os.path.isfile(filepath):
                size = os.path.getsize(filepath)
                files.append({
                    "name": name,
                    "size": size,
                    "size_human": _format_size(size),
                })
    return jsonify(files)


@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No se seleccionó ningún archivo"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Nombre de archivo vacío"}), 400

    filename = secure_filename(file.filename)
    if not filename:
        return jsonify({"error": "Nombre de archivo no válido"}), 400

    filepath = _safe_path(INPUT_DIR, filename)
    file.save(filepath)
    return jsonify({"message": f"Archivo {filename} subido exitosamente", "filename": filename})


@app.route("/api/convert", methods=["POST"])
def start_conversion():
    if transcoder.is_busy:
        return jsonify({"error": "Ya hay una conversión en progreso"}), 409

    data = request.get_json()
    if not data or not data.get("filename"):
        return jsonify({"error": "No se especificó el archivo"}), 400

    filename = data["filename"]
    delete_source = data.get("delete_source", False)

    try:
        input_path = _safe_path(INPUT_DIR, filename)
    except ValueError:
        return jsonify({"error": "Nombre de archivo no válido"}), 400

    if not os.path.exists(input_path):
        return jsonify({"error": "Archivo no encontrado"}), 404

    name, _ = os.path.splitext(filename)
    output_path = os.path.join(OUTPUT_DIR, f"{name}.mp4")

    thread = threading.Thread(
        target=transcoder.transcode,
        args=(input_path, output_path, delete_source),
        daemon=True,
    )
    thread.start()

    return jsonify({"message": "Conversión iniciada", "filename": filename})


@app.route("/api/progress")
def progress():
    filename = request.args.get("filename")
    if not filename:
        return jsonify({"error": "Falta el nombre del archivo"}), 400

    def generate():
        while True:
            data = transcoder.get_progress(filename)
            if data:
                yield f"data: {json.dumps(data)}\n\n"
                if data["status"] in ("complete", "error"):
                    break
            else:
                yield f'data: {{"status": "waiting"}}\n\n'
            time.sleep(0.5)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/outputs")
def list_outputs():
    files = []
    if os.path.exists(OUTPUT_DIR):
        for name in sorted(os.listdir(OUTPUT_DIR)):
            filepath = os.path.join(OUTPUT_DIR, name)
            if os.path.isfile(filepath):
                size = os.path.getsize(filepath)
                files.append({
                    "name": name,
                    "size": size,
                    "size_human": _format_size(size),
                })
    return jsonify(files)


@app.route("/api/download/<path:filename>")
def download_file(filename):
    try:
        _safe_path(OUTPUT_DIR, filename)
    except ValueError:
        return jsonify({"error": "Ruta no válida"}), 400
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


@app.route("/api/test-notification", methods=["POST"])
def test_notification():
    data = request.get_json()
    if not data or "type" not in data:
        return jsonify({"error": "Tipo de notificación no especificado"}), 400

    success = data["type"] == "success"
    transcoder._notify("archivo_de_prueba.mov", success=success,
                       error="Este es un error de prueba" if not success else None)
    return jsonify({"message": "Notificación de prueba enviada"})


@app.route("/api/status")
def status():
    return jsonify({"busy": transcoder.is_busy})


if __name__ == "__main__":
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=5000, threaded=True)
