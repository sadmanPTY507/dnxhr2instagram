import json
import os
import subprocess
import threading
import time

import requests


class Transcoder:
    def __init__(self):
        self._progress = {}
        self._lock = threading.Lock()
        self._busy = False

    @property
    def is_busy(self):
        return self._busy

    def get_progress(self, filename):
        with self._lock:
            return self._progress.get(filename, {}).copy()

    def _set_progress(self, filename, data):
        with self._lock:
            self._progress[filename] = data

    def get_duration(self, filepath):
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            filepath,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        info = json.loads(result.stdout)

        if "format" in info and "duration" in info["format"]:
            return float(info["format"]["duration"])

        for stream in info.get("streams", []):
            if "duration" in stream:
                return float(stream["duration"])

        raise ValueError("No se pudo determinar la duración del archivo")

    def transcode(self, input_path, output_path, delete_source=False):
        filename = os.path.basename(input_path)
        self._busy = True
        self._set_progress(filename, {
            "percent": 0, "eta": None, "status": "processing", "error": None,
        })

        try:
            duration = self.get_duration(input_path)
        except (subprocess.CalledProcessError, ValueError) as exc:
            error = f"Error al analizar el archivo: {exc}"
            self._set_progress(filename, {
                "percent": 0, "eta": None, "status": "error", "error": error,
            })
            self._notify(filename, success=False, error=error)
            self._busy = False
            return

        cpu_cores = os.environ.get("CPU_CORES", "3")
        crf = os.environ.get("FFMPEG_CRF", "18")
        preset = os.environ.get("FFMPEG_PRESET", "slow")

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-c:v", "libx264",
            "-crf", crf,
            "-preset", preset,
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "256k",
            "-ac", "2",
            "-threads", cpu_cores,
            "-movflags", "+faststart",
            "-progress", "pipe:1",
            "-nostats",
            output_path,
        ]

        try:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )

            start_time = time.time()

            for line in process.stdout:
                line = line.strip()
                if not line.startswith("out_time_us="):
                    continue
                try:
                    time_us = int(line.split("=")[1])
                    if time_us < 0:
                        continue
                    time_s = time_us / 1_000_000
                    percent = min(99.9, (time_s / duration) * 100)
                    elapsed = time.time() - start_time
                    if percent > 0:
                        total_est = elapsed / (percent / 100)
                        eta = max(0, round(total_est - elapsed))
                    else:
                        eta = None
                    self._set_progress(filename, {
                        "percent": round(percent, 1),
                        "eta": eta,
                        "status": "processing",
                        "error": None,
                    })
                except (ValueError, ZeroDivisionError):
                    pass

            process.wait()

            if process.returncode != 0:
                stderr_output = process.stderr.read()
                raise subprocess.CalledProcessError(
                    process.returncode, cmd, stderr=stderr_output,
                )

            self._set_progress(filename, {
                "percent": 100, "eta": 0, "status": "complete", "error": None,
            })

            if delete_source and os.path.exists(input_path):
                os.remove(input_path)

            self._notify(filename, success=True)

        except subprocess.CalledProcessError as exc:
            error = exc.stderr if exc.stderr else str(exc)
            self._set_progress(filename, {
                "percent": 0, "eta": None, "status": "error", "error": error,
            })
            if os.path.exists(output_path):
                os.remove(output_path)
            self._notify(filename, success=False, error=error)

        finally:
            self._busy = False

    def _notify(self, filename, success, error=None):
        ntfy_url = os.environ.get("NTFY_URL", "https://ntfy.sh")
        ntfy_topic = os.environ.get("NTFY_TOPIC", "pi-transcoding")

        if success:
            title = "Transcodificación exitosa"
            message = f"El archivo {filename} fue convertido exitosamente."
            priority = "3"
            tags = "white_check_mark"
        else:
            title = "Error en transcodificación"
            message = f"Error al convertir {filename}: {error}"
            priority = "4"
            tags = "x"

        try:
            requests.post(
                f"{ntfy_url}/{ntfy_topic}",
                headers={"Title": title, "Priority": priority, "Tags": tags},
                data=message.encode("utf-8"),
                timeout=10,
            )
        except requests.RequestException:
            pass
