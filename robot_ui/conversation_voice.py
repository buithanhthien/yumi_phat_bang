"""Local Vietnamese recording, transcription and speech playback."""
from pathlib import Path
import os
import subprocess
import tempfile
import time


class VietnameseVoice:
    def __init__(self):
        self.recognizer = None
        self.tts = None
        self.style = None

    def transcribe(self, finish, closed):
        import numpy as np
        import pyaudio
        import sherpa_onnx

        audio = pyaudio.PyAudio()
        stream = None
        frames = []
        try:
            device = os.getenv('YUMI_MIC_DEVICE')
            stream = audio.open(
                format=pyaudio.paInt16, channels=1, rate=16000, input=True,
                input_device_index=int(device) if device else None,
                frames_per_buffer=1024,
            )
            deadline = time.monotonic() + 60
            while not finish.is_set() and not closed.is_set() and time.monotonic() < deadline:
                frames.append(stream.read(1024, exception_on_overflow=False))
        finally:
            try:
                if stream is not None:
                    stream.close()
            finally:
                audio.terminate()
        if not frames or closed.is_set():
            return ''
        if self.recognizer is None:
            directory = Path(os.getenv('YUMI_GIPFORMER_DIR', '~/.cache/gipformer')).expanduser()
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
                encoder=str(directory / 'encoder-epoch-35-avg-6.onnx'),
                decoder=str(directory / 'decoder-epoch-35-avg-6.onnx'),
                joiner=str(directory / 'joiner-epoch-35-avg-6.onnx'),
                tokens=str(directory / 'tokens.txt'),
                num_threads=2, sample_rate=16000, feature_dim=80,
                decoding_method='greedy_search',
            )
        samples = np.frombuffer(b''.join(frames), dtype='<i2').astype(np.float32) / 32768
        utterance = self.recognizer.create_stream()
        utterance.accept_waveform(16000, samples)
        self.recognizer.decode_stream(utterance)
        return utterance.result.text.strip()

    def speak(self, text, cancel):
        if cancel.is_set():
            return
        if self.tts is None:
            from supertonic import TTS
            tts = TTS(auto_download=False)
            style = tts.get_voice_style(voice_name='F1')
            self.tts, self.style = tts, style
        wav, _ = self.tts.synthesize(text=text, voice_style=self.style, lang='vi')
        if cancel.is_set():
            return
        with tempfile.TemporaryDirectory(prefix='yumi-voice-') as directory:
            path = str(Path(directory) / 'reply.wav')
            self.tts.save_audio(wav, path)
            command = ['aplay', '-q']
            if device := os.getenv('YUMI_SPEAKER_DEVICE'):
                command.extend(['-D', device])
            with subprocess.Popen([*command, path], stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL) as player:
                while player.poll() is None:
                    if cancel.wait(0.1):
                        player.kill()
                        return
                if player.returncode:
                    raise RuntimeError('Không phát được âm thanh')
