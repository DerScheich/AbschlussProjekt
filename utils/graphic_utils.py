import cv2
import numpy as np
import tempfile
import subprocess
import os
from io import BytesIO
from PIL import Image


class GraphicUtils:
    # ========== Schwarz-Weiß-Konvertierung ==========
    def convert_to_grayscale_image(self, image_bytes: bytes) -> bytes:
        """Konvertiert ein Bild in Graustufen."""
        img_array = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        success, encoded = cv2.imencode(".png", gray)
        if not success:
            raise ValueError("Fehler bei der Bildkonvertierung")
        return encoded.tobytes()

    def convert_to_grayscale_video(self, video_bytes: bytes) -> bytes:
        """Konvertiert ein Video in Graustufen mit FFmpeg."""
        temp_dir = tempfile.gettempdir()
        temp_input = os.path.join(temp_dir, "sw_input.mp4")
        final_output = os.path.join(temp_dir, "sw_output.mp4")

        with open(temp_input, "wb") as f:
            f.write(video_bytes)

        command = [
            "ffmpeg", "-y",
            "-i", temp_input,
            "-vf", "format=gray",  # FFmpeg Graustufen-Filter
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "copy",  # Behalte Original-Audio bei
            final_output
        ]

        result = subprocess.run(command, capture_output=True)
        if result.returncode != 0:
            raise Exception(f"FFmpeg Fehler: {result.stderr.decode('utf-8')}")

        with open(final_output, "rb") as f:
            return f.read()

    # ========== Wasserzeichen-Funktionen (Original aus WatermarkHandler) ==========
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

        # Animierte GIF-Wasserzeichen
        if watermark_bytes[:6] in (b'GIF87a', b'GIF89a'):
            temp_wm = os.path.join(temp_dir, "watermark_tempwatermark.gif")
            with open(temp_wm, "wb") as f:
                f.write(watermark_bytes)
            cap = cv2.VideoCapture(temp_input)
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            im = Image.open(BytesIO(watermark_bytes))
            wm_w, wm_h = im.size
            scaled_w = int(wm_w * scale)
            scaled_h = int(wm_h * scale)
            positions = {
                "top-left": (0, 0),
                "top-right": (width - scaled_w, 0),
                "bottom-left": (0, height - scaled_h),
                "bottom-right": (width - scaled_w, height - scaled_h),
                "center": ((width - scaled_w) // 2, (height - scaled_h) // 2)
            }
            x, y = positions.get(position, positions["center"])
            command = [
                "ffmpeg", "-y",
                "-i", temp_input,
                "-ignore_loop", "0",
                "-i", temp_wm,
                "-filter_complex", f"overlay={x}:{y}:format=auto:shortest=1",
                "-c:v", "libx264", "-preset", "veryfast",
                "-c:a", "aac",
                final_output
            ]
            result = subprocess.run(command, capture_output=True)
            if result.returncode != 0:
                raise Exception("FFmpeg Error: " + result.stderr.decode("utf-8"))

        # Statische Wasserzeichen
        else:
            wm_array = np.frombuffer(watermark_bytes, np.uint8)
            wm_img = cv2.imdecode(wm_array, cv2.IMREAD_UNCHANGED)
            cap = cv2.VideoCapture(temp_input)
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            out_vid = cv2.VideoWriter(temp_video, fourcc, fps, (width, height))
            while cap.isOpened():
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
                "-c:v", "libx264", "-preset", "veryfast",
                "-c:a", "aac",
                final_output
            ]
            result = subprocess.run(command, capture_output=True)

        with open(final_output, "rb") as f:
            return f.read()

    def watermark_image_file(self, image_bytes: bytes, watermark_bytes: bytes, position: str,
                             scale: float, transparency: float) -> bytes:
        in_array = np.frombuffer(image_bytes, np.uint8)
        in_img = cv2.imdecode(in_array, cv2.IMREAD_COLOR)
        wm_array = np.frombuffer(watermark_bytes, np.uint8)
        wm_img = cv2.imdecode(wm_array, cv2.IMREAD_UNCHANGED)
        if in_img is None or wm_img is None:
            raise ValueError("Ungültige Eingabedateien")
        result = self.add_watermark_image(in_img, wm_img, position, scale, transparency)
        success, encoded = cv2.imencode(".png", result)
        if not success:
            raise ValueError("Fehler beim Kodieren des Ergebnisbildes")
        return encoded.tobytes()