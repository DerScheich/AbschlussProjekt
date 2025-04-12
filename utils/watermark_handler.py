import os
import cv2
import numpy as np
import tempfile
import subprocess

from PIL import Image
from io import BytesIO


class WatermarkHandler:
    """Enthält Funktionen zum Hinzufügen von Wasserzeichen zu Bildern und Videos."""

    def add_watermark_image(self, image: np.ndarray, watermark: np.ndarray, position: str = "center",
                            scale: float = 1.0, transparency: float = 1.0) -> np.ndarray:
        wH, wW = watermark.shape[:2]
        scaled_width = int(wW * scale)
        scaled_height = int(wH * scale)
        watermark_resized = cv2.resize(watermark, (scaled_width, scaled_height), interpolation=cv2.INTER_AREA)
        h, w = image.shape[:2]
        wH2, wW2 = watermark_resized.shape[:2]
        positions = {
            "top-left": (0, 0),
            "top-right": (w - wW2, 0),
            "bottom-left": (0, h - wH2),
            "bottom-right": (w - wW2, h - wH2),
            "center": ((w - wW2) // 2, (h - wH2) // 2)
        }
        if position not in positions:
            position = "center"
        x, y = positions[position]
        if x < 0 or y < 0 or (x + wW2 > w) or (y + wH2 > h):
            return image
        roi = image[y:y + wH2, x:x + wW2]
        if watermark_resized.shape[2] == 4:
            alpha_channel = watermark_resized[:, :, 3] / 255.0 * transparency
            color_channels = watermark_resized[:, :, :3]
        else:
            alpha_channel = np.ones((wH2, wW2), dtype=np.float32) * transparency
            color_channels = watermark_resized
        for c in range(3):
            roi[:, :, c] = alpha_channel * color_channels[:, :, c] + (1 - alpha_channel) * roi[:, :, c]
        image[y:y + wH2, x:x + wW2] = roi
        return image

    def watermark_video_file(self, video_bytes: bytes, watermark_bytes: bytes, position: str,
                             scale: float, transparency: float) -> bytes:
        temp_dir = tempfile.gettempdir()
        temp_input = os.path.join(temp_dir, "watermark_inputvideo.mp4")
        temp_video = os.path.join(temp_dir, "watermark_tempvideo.mp4")
        final_output = os.path.join(temp_dir, "watermark_final_output.mp4")

        with open(temp_input, "wb") as f:
            f.write(video_bytes)

        # Prüfe, ob das Wasserzeichen ein animiertes GIF ist
        if watermark_bytes[:6] in (b'GIF87a', b'GIF89a'):
            # Wasserzeichen als animiertes GIF speichern
            temp_wm = os.path.join(temp_dir, "watermark_tempwatermark.gif")
            with open(temp_wm, "wb") as f:
                f.write(watermark_bytes)
            # Ermittle Videodimensionen mittels OpenCV
            cap = cv2.VideoCapture(temp_input)
            if not cap.isOpened():
                raise ValueError("Eingabevideo konnte nicht geöffnet werden.")
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            try:
                im = Image.open(BytesIO(watermark_bytes))
                wm_w, wm_h = im.size
            except Exception as e:
                raise ValueError("Wasserzeichen-GIF konnte nicht decodiert werden.")
            scaled_w = int(wm_w * scale)
            scaled_h = int(wm_h * scale)
            positions = {
                "top-left": (0, 0),
                "top-right": (width - scaled_w, 0),
                "bottom-left": (0, height - scaled_h),
                "bottom-right": (width - scaled_w, height - scaled_h),
                "center": ((width - scaled_w) // 2, (height - scaled_h) // 2)
            }
            if position not in positions:
                position = "center"
            x, y = positions[position]
            # FFmpeg-Befehl: Overlay des animierten GIFs
            command = [
                "ffmpeg", "-y",
                "-i", temp_input,
                "-ignore_loop", "0",
                "-i", temp_wm,
                "-filter_complex", f"overlay={x}:{y}:format=auto:shortest=1",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-c:a", "aac",
                "-map", "0:v:0",
                "-map", "0:a:0",
                "-shortest",
                final_output
            ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                raise Exception("FFmpeg Error: " + result.stderr.decode("utf-8"))
            with open(final_output, "rb") as f:
                result_bytes = f.read()
            return result_bytes
        else:
            # Wasserzeichen ist ein statisches Bild
            wm_array = np.frombuffer(watermark_bytes, np.uint8)
            wm_img = cv2.imdecode(wm_array, cv2.IMREAD_UNCHANGED)
            if wm_img is None:
                raise ValueError("Wasserzeichen-Datei konnte nicht als Bild decodiert werden.")
            cap = cv2.VideoCapture(temp_input)
            if not cap.isOpened():
                raise ValueError("Eingabevideo konnte nicht geöffnet werden.")
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            out_vid = cv2.VideoWriter(temp_video, fourcc, fps, (width, height))
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_result = self.add_watermark_image(frame, wm_img, position, scale, transparency)
                out_vid.write(frame_result)
            cap.release()
            out_vid.release()
            command = [
                "ffmpeg", "-y",
                "-i", temp_video,
                "-i", temp_input,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-c:a", "aac",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
                final_output
            ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                raise Exception("FFmpeg Error: " + result.stderr.decode("utf-8"))
            with open(final_output, "rb") as f:
                result_bytes = f.read()
            return result_bytes

    def watermark_image_file(self, image_bytes: bytes, watermark_bytes: bytes, position: str,
                             scale: float, transparency: float) -> bytes:
        in_array = np.frombuffer(image_bytes, np.uint8)
        in_img = cv2.imdecode(in_array, cv2.IMREAD_COLOR)
        wm_array = np.frombuffer(watermark_bytes, np.uint8)
        wm_img = cv2.imdecode(wm_array, cv2.IMREAD_UNCHANGED)
        if in_img is None or wm_img is None:
            raise ValueError("Eingabedatei oder Wasserzeichen nicht decodierbar als Bild.")
        result = self.add_watermark_image(in_img, wm_img, position, scale, transparency)
        success, encoded = cv2.imencode(".png", result)
        if not success:
            raise ValueError("Fehler beim Kodieren des Ergebnis-Bildes.")
        return encoded.tobytes()
