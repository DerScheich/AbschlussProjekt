import cv2
import numpy as np
import tempfile
import subprocess
import os
from io import BytesIO
from PIL import Image

class GraphicUtils:
    """
    Bietet Bild- und Videobearbeitungsfunktionen (Graustufen, Wasserzeichen).
    """
    def convert_to_grayscale_image(self, image_bytes: bytes) -> bytes:
        """
        Wandelt ein Bild in Graustufen um.

        :param image_bytes: Eingabebild als Bytes.
        :return: Graustufenbild als PNG-Bytes.
        """
        # Bytes in NumPy-Array laden
        img_array = np.frombuffer(image_bytes, np.uint8)
        # Bild dekodieren
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        # Graustufen konvertieren
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Ergebnis kodieren
        success, encoded = cv2.imencode('.png', gray)
        if not success:
            raise ValueError('Fehler bei der Bildkonvertierung')
        return encoded.tobytes()

    def convert_to_grayscale_video(self, video_bytes: bytes) -> bytes:
        """
        Wandelt ein Video in Graustufen um.

        :param video_bytes: Eingabevideo als Bytes.
        :return: Graustufenvideo als MP4-Bytes.
        """
        # Temporäre Dateien
        temp_dir = tempfile.gettempdir()
        in_file = os.path.join(temp_dir, 'sw_input.mp4')
        out_file = os.path.join(temp_dir, 'sw_output.mp4')
        # Video speichern
        with open(in_file, 'wb') as f:
            f.write(video_bytes)
        # FFmpeg Graustufen-Filter
        cmd = [
            'ffmpeg', '-y', '-i', in_file,
            '-vf', 'format=gray', '-c:v', 'libx264', '-preset', 'fast',
            '-c:a', 'copy', out_file
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise Exception(f'FFmpeg Fehler: {result.stderr.decode()}')
        # Ausgabedatei lesen
        with open(out_file, 'rb') as f:
            return f.read()

    def add_watermark_image(self, image: np.ndarray, watermark: np.ndarray,
                            position: str = 'center', scale: float = 1.0,
                            transparency: float = 1.0) -> np.ndarray:
        """
        Fügt ein Bildwasserzeichen hinzu.

        :param image: Originalbild als NumPy-Array.
        :param watermark: Wasserzeichenbild (RGBA oder RGB) als Array.
        :param position: Position (top-left, center, etc.).
        :param scale: Skalierungsfaktor.
        :param transparency: Transparenz 0.0–1.0.
        :return: Bild mit Wasserzeichen als Array.
        """
        # Wasserzeichen skalieren
        h_wm, w_wm = watermark.shape[:2]
        nw, nh = int(w_wm * scale), int(h_wm * scale)
        wm_resized = cv2.resize(watermark, (nw, nh), interpolation=cv2.INTER_AREA)
        h, w = image.shape[:2]
        # Position berechnen
        pos_map = {
            'top-left': (0, 0),
            'top-right': (w-nw, 0),
            'bottom-left': (0, h-nh),
            'bottom-right': (w-nw, h-nh),
            'center': ((w-nw)//2, (h-nh)//2)
        }
        x, y = pos_map.get(position, pos_map['center'])
        # ROI ausschneiden
        roi = image[y:y+nh, x:x+nw]
        # Alpha-Kanal extrahieren
        if wm_resized.shape[2] == 4:
            alpha = wm_resized[:, :, 3] / 255.0 * transparency
            wm_rgb = wm_resized[:, :, :3]
        else:
            alpha = np.full((nh, nw), transparency, dtype=float)
            wm_rgb = wm_resized
        # Überlagerung
        for c in range(3):
            roi[:, :, c] = alpha * wm_rgb[:, :, c] + (1-alpha) * roi[:, :, c]
        image[y:y+nh, x:x+nw] = roi
        return image

    def watermark_video_file(self, video_bytes: bytes, watermark_bytes: bytes,
                             position: str, scale: float, transparency: float) -> bytes:
        """
        Fügt Wasserzeichen zu Video hinzu (GIF oder statisch).

        :param video_bytes: Eingabevideo als Bytes.
        :param watermark_bytes: Wasserzeichen-Datei als Bytes.
        :param position: Position des Wasserzeichens.
        :param scale: Skalierung.
        :param transparency: Transparenz.
        :return: Video mit Wasserzeichen als Bytes.
        """
        temp_dir = tempfile.gettempdir()
        in_vid = os.path.join(temp_dir, 'wm_in.mp4')
        temp_vid = os.path.join(temp_dir, 'wm_temp.mp4')
        out_vid = os.path.join(temp_dir, 'wm_out.mp4')
        # Bytes speichern
        with open(in_vid, 'wb') as f:
            f.write(video_bytes)
        # GIF-Wasserzeichen
        if watermark_bytes[:6] in (b'GIF87a', b'GIF89a'):
            gif_file = os.path.join(temp_dir, 'wm.gif')
            with open(gif_file, 'wb') as f:
                f.write(watermark_bytes)
            # Video-Metadaten
            cap = cv2.VideoCapture(in_vid)
            fps = cap.get(cv2.CAP_PROP_FPS)
            w_vid = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h_vid = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            # GIF-Overlay via FFmpeg
            im = Image.open(BytesIO(watermark_bytes))
            w_gif, h_gif = im.size
            w_g, h_g = int(w_gif*scale), int(h_gif*scale)
            coords = {
                'top-left': (0,0), 'top-right': (w_vid-w_g,0),
                'bottom-left': (0,h_vid-h_g), 'bottom-right': (w_vid-w_g,h_vid-h_g),
                'center': ((w_vid-w_g)//2,(h_vid-h_g)//2)
            }
            x, y = coords.get(position, coords['center'])
            cmd = [
                'ffmpeg','-y','-i',in_vid,'-ignore_loop','0','-i',gif_file,
                '-filter_complex',f'overlay={x}:{y}:shortest=1',
                '-c:v','libx264','-preset','veryfast','-c:a','aac',out_vid
            ]
            res = subprocess.run(cmd, capture_output=True)
            if res.returncode != 0:
                raise Exception(f'FFmpeg Error: {res.stderr.decode()}')
        else:
            # Statisches Wasserzeichen auf Frames
            wm_arr = np.frombuffer(watermark_bytes, np.uint8)
            wm_img = cv2.imdecode(wm_arr, cv2.IMREAD_UNCHANGED)
            cap = cv2.VideoCapture(in_vid)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            fps = cap.get(cv2.CAP_PROP_FPS)
            w_vid = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h_vid = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            out_temp = cv2.VideoWriter(temp_vid, fourcc, fps, (w_vid, h_vid))
            # Frame-Loop
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frm = self.add_watermark_image(frame, wm_img, position, scale, transparency)
                out_temp.write(frm)
            cap.release()
            out_temp.release()
            # Audio beibehalten
            cmd2 = ['ffmpeg','-y','-i',temp_vid,'-i',in_vid,'-c:v','libx264','-preset','veryfast','-c:a','aac',out_vid]
            subprocess.run(cmd2, capture_output=True)
        # Ausgabedatei lesen
        with open(out_vid, 'rb') as f:
            return f.read()

    def watermark_image_file(self, image_bytes: bytes, watermark_bytes: bytes,
                             position: str, scale: float, transparency: float) -> bytes:
        """
        Fügt Wasserzeichen zu Bild hinzu.

        :param image_bytes: Eingabebild als Bytes.
        :param watermark_bytes: Wasserzeichen als Bytes.
        :param position: Position.
        :param scale: Skalierung.
        :param transparency: Transparenz.
        :return: Bild mit Wasserzeichen als PNG-Bytes.
        """
        # Bytes dekodieren
        in_arr = np.frombuffer(image_bytes, np.uint8)
        in_img = cv2.imdecode(in_arr, cv2.IMREAD_COLOR)
        wm_arr = np.frombuffer(watermark_bytes, np.uint8)
        wm_img = cv2.imdecode(wm_arr, cv2.IMREAD_UNCHANGED)
        if in_img is None or wm_img is None:
            raise ValueError('Ungültige Eingabedateien')
        # Wasserzeichen anwenden
        res = self.add_watermark_image(in_img, wm_img, position, scale, transparency)
        # Ergebnis kodieren
        ok, enc = cv2.imencode('.png', res)
        if not ok:
            raise ValueError('Fehler beim Kodieren des Ergebnisbildes')
        return enc.tobytes()