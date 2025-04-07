import io
import numpy as np
from scipy import signal
from scipy.io import wavfile
from pydub import AudioSegment
import discord

class AudioEffects:
    """Enthält alle Audiofunktionen zum Laden und Bearbeiten von Audiodateien."""

    @staticmethod
    async def load_audio_from_attachment(attachment: discord.Attachment) -> tuple[int, np.ndarray]:
        file_bytes = await attachment.read()
        name_lower = attachment.filename.lower()

        if name_lower.endswith(".wav"):
            with io.BytesIO(file_bytes) as f:
                rate, data = wavfile.read(f)
            return rate, data
        elif name_lower.endswith(".mp3"):
            audio_seg = AudioSegment.from_file(io.BytesIO(file_bytes), format="mp3")
            samples = np.array(audio_seg.get_array_of_samples())
            rate = audio_seg.frame_rate
            if audio_seg.channels == 2:
                samples = samples.reshape((-1, 2))
            return rate, samples
        else:
            raise ValueError("Es sind nur .wav oder .mp3 erlaubt.")

    @staticmethod
    def refined_resample_audio(audio: np.ndarray, orig_rate: int, target_rate: int) -> np.ndarray:
        if orig_rate == target_rate:
            return audio
        target_length = int(len(audio) * target_rate / orig_rate)
        return signal.resample(audio, target_length)

    @staticmethod
    def refined_convolve_audio(x: np.ndarray, h: np.ndarray) -> np.ndarray:
        if x.ndim == 1:
            x = np.expand_dims(x, axis=1)
        if h.ndim == 1:
            h = np.expand_dims(h, axis=1)

        if x.shape[1] == 1 and h.shape[1] == 1:
            y = signal.fftconvolve(x[:, 0], h[:, 0], mode="full")
            y = np.column_stack((y, y))  # Stereo
        elif x.shape[1] == 1 and h.shape[1] == 2:
            left = signal.fftconvolve(x[:, 0], h[:, 0], mode="full")
            right = signal.fftconvolve(x[:, 0], h[:, 1], mode="full")
            y = np.column_stack((left, right))
        elif x.shape[1] == 2 and h.shape[1] == 1:
            left = signal.fftconvolve(x[:, 0], h[:, 0], mode="full")
            right = signal.fftconvolve(x[:, 1], h[:, 0], mode="full")
            y = np.column_stack((left, right))
        else:
            left = signal.fftconvolve(x[:, 0], h[:, 0], mode="full")
            right = signal.fftconvolve(x[:, 1], h[:, 1], mode="full")
            y = np.column_stack((left, right))

        max_val = np.max(np.abs(y))
        if max_val > 0:
            y /= max_val
        return y

    @staticmethod
    def slow_audio(data: np.ndarray, slow_factor: float = 0.85) -> np.ndarray:
        new_len = int(len(data) / slow_factor)
        if data.ndim == 1:
            slowed = signal.resample(data, new_len)
        else:
            left = signal.resample(data[:, 0], new_len)
            right = signal.resample(data[:, 1], new_len)
            slowed = np.column_stack((left, right))
        max_val = np.max(np.abs(slowed))
        if max_val > 0:
            slowed /= max_val
        return slowed
