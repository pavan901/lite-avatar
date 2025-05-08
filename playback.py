import time
import asyncio
from fractions import Fraction
import numpy as np
from av import AudioFrame, VideoFrame
from videosdk import CustomAudioTrack, CustomVideoTrack

AUDIO_SAMPLE_RATE = 16000
SAMPLES_PER_FRAME = 320
BYTES_PER_FRAME = SAMPLES_PER_FRAME * 2

class PreRenderedAudioTrack(CustomAudioTrack):
    kind = "audio"
    readyState = "live"

    def __init__(self, audio_bytes: bytes, start_time):
        super().__init__()
        self.audio_frames = self._generate_audio_frames(audio_bytes)
        self.index = 0
        self.start_time = start_time

    def _generate_audio_frames(self, audio_bytes):
        chunks = [audio_bytes[i:i + BYTES_PER_FRAME] for i in range(0, len(audio_bytes), BYTES_PER_FRAME)]
        frames = []
        for i, chunk in enumerate(chunks):
            data = np.frombuffer(chunk, dtype=np.int16).reshape(-1, 1)
            frame = AudioFrame.from_ndarray(data.T, format="s16", layout="mono")
            frame.pts = i * SAMPLES_PER_FRAME
            frame.sample_rate = AUDIO_SAMPLE_RATE
            frame.time_base = Fraction(1, AUDIO_SAMPLE_RATE)
            frames.append(frame)
        return frames

    async def recv(self) -> AudioFrame:
        if self.index >= len(self.audio_frames):
            await asyncio.sleep(0.02)
            return self.audio_frames[-1]
        frame = self.audio_frames[self.index]
        expected_time = self.start_time + (frame.pts / AUDIO_SAMPLE_RATE)
        now = time.time()
        if expected_time > now:
            await asyncio.sleep(expected_time - now)
        self.index += 1
        return frame

class StreamingVideoTrack(CustomVideoTrack):
    kind = "video"
    readyState = "live"

    def __init__(self, queue, fps: int, ready_event, start_time):
        super().__init__()
        self.queue = queue
        self.fps = fps
        self.index = 0
        self.time_base = Fraction(1, fps)
        self.start_time = start_time

        print("[VideoTrack] Waiting for readiness signal...")
        ready_event.wait()
        print("[VideoTrack] Starting video stream.")

    async def recv(self) -> VideoFrame:
        frame_np = self.queue.get()
        expected_time = self.start_time + (self.index / self.fps)
        now = time.time()
        if expected_time > now:
            await asyncio.sleep(expected_time - now)
        frame = VideoFrame.from_ndarray(frame_np, format="bgr24")
        frame.pts = self.index
        frame.time_base = self.time_base
        self.index += 1
        return frame
