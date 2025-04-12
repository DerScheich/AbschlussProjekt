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

    @staticmethod
    def mono_to_stereo(mono_audio: np.ndarray, rate: int, delay_ms: int = 20) -> np.ndarray:
        """
        Wandelt ein Mono-Signal in ein Stereo-Signal um, indem nur Frequenzen über 100 Hz
        stereoized werden. Subbass-Frequenzen unter 100 Hz bleiben in beiden Kanälen identisch.
        """
        # Konvertiere das Signal in den Bereich [-1, 1], falls es nicht bereits float ist.
        if not np.issubdtype(mono_audio.dtype, np.floating):
            mono_audio = mono_audio.astype(np.float32) / 32767.0

        # Berechne den Nyquist-Frequenzwert und definiere den Cutoff.
        nyquist = rate / 2.0
        cutoff = 100.0

        # Erstelle einen 4. Ordnung Butterworth Low-Pass Filter für den Subbass.
        b_low, a_low = signal.butter(4, cutoff / nyquist, btype='low')
        low_freq = signal.filtfilt(b_low, a_low, mono_audio)

        # Highpass-Bereich: Entferne den Subbassanteil vom Originalsignal.
        high_freq = mono_audio - low_freq

        # Linker Kanal: Subbass + High-Frequenzen (unverändert).
        left = low_freq + high_freq

        # Rechter Kanal: Subbass + High-Frequenzen (um delay_ms verzögert).
        delay_samples = int(rate * delay_ms / 1000)
        delayed_high = np.concatenate((np.zeros(delay_samples, dtype=high_freq.dtype), high_freq))
        delayed_high = delayed_high[:len(high_freq)]
        right = low_freq + delayed_high

        # Kombiniere beide Kanäle zu einem Stereo-Signal.
        stereo = np.column_stack((left, right))

        # Normiere das Ergebnis, um Clipping zu vermeiden.
        max_val = np.max(np.abs(stereo))
        if max_val > 0:
            stereo = stereo / max_val

        return stereo

    @staticmethod
    def stereo_to_mono(stereo_audio: np.ndarray) -> np.ndarray:
        """
        Wandelt ein Stereo-Signal in ein Mono-Signal um, indem beide Kanäle gemittelt werden.
        """
        if not np.issubdtype(stereo_audio.dtype, np.floating):
            stereo_audio = stereo_audio.astype(np.float32) / 32767.0

        mono = np.mean(stereo_audio, axis=1)
        max_val = np.max(np.abs(mono))
        if max_val > 0:
            mono = mono / max_val
        return mono