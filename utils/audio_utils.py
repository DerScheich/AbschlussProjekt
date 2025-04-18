import io
import numpy as np
from scipy import signal
from scipy.io import wavfile
from pydub import AudioSegment
import discord

class AudioEffects:
    """
    Bietet Methoden zum Laden und Bearbeiten von Audiodateien.
    """
    @staticmethod
    async def load_audio_from_attachment(attachment: discord.Attachment) -> tuple[int, np.ndarray]:
        """
        Liest Audio aus Discord-Attachment ein (.wav oder .mp3).

        :param attachment: Discord Attachment mit Audiodatei.
        :return: Tuple(rate, Audio-Daten als NumPy-Array).
        """
        file_bytes = await attachment.read()
        name = attachment.filename.lower()
        # WAV-Datei
        if name.endswith('.wav'):
            with io.BytesIO(file_bytes) as f:
                rate, data = wavfile.read(f)
            return rate, data
        # MP3-Datei
        if name.endswith('.mp3'):
            seg = AudioSegment.from_file(io.BytesIO(file_bytes), format='mp3')
            samples = np.array(seg.get_array_of_samples())
            rate = seg.frame_rate
            # Stereo umformen
            if seg.channels == 2:
                samples = samples.reshape((-1, 2))
            return rate, samples
        raise ValueError('Nur .wav oder .mp3 unterstützt')

    @staticmethod
    def refined_resample_audio(audio: np.ndarray, orig_rate: int, target_rate: int) -> np.ndarray:
        """
        Resampled Audio auf neue Abtastrate mit FFT.

        :param audio: Originale Audiodaten.
        :param orig_rate: Originalrate.
        :param target_rate: Zielrate.
        :return: Resampltes Audio.
        """
        if orig_rate == target_rate:
            return audio
        length = int(len(audio) * target_rate / orig_rate)
        return signal.resample(audio, length)

    @staticmethod
    def refined_convolve_audio(x: np.ndarray, h: np.ndarray) -> np.ndarray:
        """
        Faltet Signal x mit Impulsantwort h (FFT-Convolution).

        :param x: Eingangssignal (NumPy-Array).
        :param h: Impulsantwort (NumPy-Array).
        :return: Ausgabesignal (Stereo Array).
        """
        # sicherstellen: 2D-Arrays
        if x.ndim == 1:
            x = x[:, None]
        if h.ndim == 1:
            h = h[:, None]
        # vier Fälle: mono/stereo-Kombinationen
        if x.shape[1] == 1 and h.shape[1] == 1:
            y = signal.fftconvolve(x[:,0], h[:,0], mode='full')
            y = np.column_stack((y, y))
        elif x.shape[1] == 1 and h.shape[1] == 2:
            l = signal.fftconvolve(x[:,0], h[:,0], mode='full')
            r = signal.fftconvolve(x[:,0], h[:,1], mode='full')
            y = np.column_stack((l, r))
        elif x.shape[1] == 2 and h.shape[1] == 1:
            l = signal.fftconvolve(x[:,0], h[:,0], mode='full')
            r = signal.fftconvolve(x[:,1], h[:,0], mode='full')
            y = np.column_stack((l, r))
        else:
            l = signal.fftconvolve(x[:,0], h[:,0], mode='full')
            r = signal.fftconvolve(x[:,1], h[:,1], mode='full')
            y = np.column_stack((l, r))
        # normalisieren
        m = np.max(np.abs(y))
        if m > 0:
            y = y / m
        return y

    @staticmethod
    def slow_audio(data: np.ndarray, slow_factor: float = 0.85) -> np.ndarray:
        """
        Verlangsamt das Audio um Faktor (längerer Stream).

        :param data: Audiodaten.
        :param slow_factor: Verlangsamungsfaktor (<1 beschleunigt).
        :return: Verlangsamtes Audio (Array).
        """
        new_len = int(len(data) / slow_factor)
        # mono oder stereo
        if data.ndim == 1:
            arr = signal.resample(data, new_len)
        else:
            l = signal.resample(data[:,0], new_len)
            r = signal.resample(data[:,1], new_len)
            arr = np.column_stack((l, r))
        # normalisieren
        m = np.max(np.abs(arr))
        if m > 0:
            arr = arr / m
        return arr

    @staticmethod
    def mono_to_stereo(mono_audio: np.ndarray, rate: int, delay_ms: int = 20) -> np.ndarray:
        """
        Wandelt Mono zu Stereo mittels Haas-Effekt.

        :param mono_audio: Mono-Signal.
        :param rate: Abtastrate.
        :param delay_ms: Verzögerung rechter Kanal.
        :return: Stereo-Signal (2D-Array).
        """
        # auf [-1,1] skalieren
        if not np.issubdtype(mono_audio.dtype, np.floating):
            mono_audio = mono_audio.astype(np.float32) / 32767.0
        # Subbass/Highsplit via Butterworth
        nyq = rate/2
        b,a = signal.butter(4, 100/nyq, btype='low')
        low = signal.filtfilt(b, a, mono_audio)
        high = mono_audio - low
        # rechter Kanal verzögern
        d = int(rate * delay_ms/1000)
        high_del = np.concatenate((np.zeros(d), high))[:len(high)]
        left = low + high
        right = low + high_del
        stereo = np.column_stack((left, right))
        # normalisieren
        m = np.max(np.abs(stereo))
        if m > 0:
            stereo = stereo / m
        return stereo

    @staticmethod
    def stereo_to_mono(stereo_audio: np.ndarray) -> np.ndarray:
        """
        Wandelt Stereo zu Mono durch Mittelung beider Kanäle.

        :param stereo_audio: Stereo-Signal (2D-Array).
        :return: Mono-Signal.
        """
        if not np.issubdtype(stereo_audio.dtype, np.floating):
            stereo_audio = stereo_audio.astype(np.float32) / 32767.0
        mono = np.mean(stereo_audio, axis=1)
        m = np.max(np.abs(mono))
        if m > 0:
            mono = mono / m
        return mono