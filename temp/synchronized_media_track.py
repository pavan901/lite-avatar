import asyncio
import time
from fractions import Fraction
import numpy as np
from av import AudioFrame, VideoFrame
from videosdk import CustomVideoTrack, CustomAudioTrack
from avatar_image_processor import AvatarImageProcessor
from modules.elevenlabs.client import ElevenLabs
from modules.elevenlabs.types.voice_settings import VoiceSettings
from modules.elevenlabs.core.request_options import RequestOptions

AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_PTIME = 0.02
SAMPLES_PER_FRAME = int(AUDIO_SAMPLE_RATE * AUDIO_PTIME)
CHUNK_SIZE = SAMPLES_PER_FRAME * AUDIO_CHANNELS * 2

class AudioVideoAligner:
    def __init__(self, fps):
        self._fps = fps

        self._current_speech_id = ""
        self._audio_byte_length_current_speech = 0
        self._audio_data_current_speech = bytearray()
        self._total_frame_count_current_speech = 0
        self._audio_start_idx = 0
        self._returned_audio_length_current_speech = 0

    def align_audio_with_frames(self, audio_data, frame_count, speech_id, end_of_speech=False):
        origin_sample_rate = AUDIO_SAMPLE_RATE

        if speech_id != self._current_speech_id:
            self._audio_byte_length_current_speech = 0
            self._audio_data_current_speech = bytearray()
            self._current_speech_id = speech_id
            self._total_frame_count_current_speech = 0
            self._audio_start_idx = 0
            self._returned_audio_length_current_speech = 0

        self._audio_data_current_speech += audio_data
        self._total_frame_count_current_speech += frame_count

        audio_length_per_frame = origin_sample_rate / self._fps * 2

        total_audio_length = int(self._total_frame_count_current_speech * audio_length_per_frame)

        if not end_of_speech:
            ret_audio = audio_data
        else:
            diff = total_audio_length - len(self._audio_data_current_speech)
            if diff > 0:
                self._audio_data_current_speech += bytearray(diff)
            else:
                self._audio_data_current_speech = self._audio_data_current_speech[:total_audio_length]
            ret_audio = self._audio_data_current_speech[self._audio_start_idx:]

        self._returned_audio_length_current_speech += len(ret_audio)
        self._audio_start_idx += len(ret_audio)

        return ret_audio

class SynchronizedMediaTrack:
    def __init__(self, loop, voice: str, elevenlabs_api_key: str, fps: int = 20):
        self.loop = loop
        self.voice = voice
        self.api_key = elevenlabs_api_key
        self.audio_buffer = bytearray()
        self.audio_pts = 0
        self.video_frame_index = 0
        self.fps = fps
        self.speech_id = 0
        self.current_speech_ended = False

        self.param_list = []
        self.param_index = 0

        self.processor = AvatarImageProcessor(queue=asyncio.Queue())
        self.avatar = self.processor.avatar
        self.queue = self.processor.queue

        self.audio_time_base = Fraction(1, AUDIO_SAMPLE_RATE)
        self.video_time_base = Fraction(1, fps)

        # ElevenLabs TTS client
        self.tts = ElevenLabs(api_key=self.api_key)

        # Audio-video aligner
        self.aligner = AudioVideoAligner(fps=fps)

        # Wrappers for VideoSDK
        self.audio_track = self.AudioWrapper(self)
        self.video_track = self.VideoWrapper(self)

    async def feed_text(self, text: str):
        self.speech_id += 1
        current_speech_id = f"speech_{self.speech_id}"
        self.current_speech_ended = False
        
        stream_data = self.tts.generate(
            text=text,
            stream=True,
            output_format="pcm_16000",
            model="eleven_multilingual_v2",
            voice=self.voice,
            voice_settings=VoiceSettings(
                stability=0.71,
                similarity_boost=0.5,
                style=0.0,
                use_speaker_boost=True,
            ),
            request_options=RequestOptions(timeout_in_seconds=300),
        )

        async def stream_and_buffer():
            frame_count = 0
            for chunk in stream_data:
                if chunk:
                    # Track frame count based on audio chunk size
                    frames_in_chunk = len(chunk) // (AUDIO_SAMPLE_RATE // self.fps * 2)
                    if frames_in_chunk == 0:
                        frames_in_chunk = 1
                    
                    frame_count += frames_in_chunk
                    
                    # Align audio with frames
                    aligned_chunk = self.aligner.align_audio_with_frames(
                        chunk, frames_in_chunk, current_speech_id, False
                    )
                    
                    self.audio_buffer.extend(aligned_chunk)
                    await self.queue.put(chunk)
            
            # Mark end of speech and finalize alignment
            self.current_speech_ended = True
            final_chunk = bytearray()
            final_aligned = self.aligner.align_audio_with_frames(
                final_chunk, 0, current_speech_id, True
            )
            if final_aligned:
                self.audio_buffer.extend(final_aligned)
                await self.queue.put(bytes(final_aligned))

        await asyncio.create_task(stream_and_buffer())

    class AudioWrapper(CustomAudioTrack):
        kind = "audio"
        readyState = "live"

        def __init__(self, parent:'SynchronizedMediaTrack'):
            super().__init__()
            self.parent = parent
            self.start_time = None
            self.last_pts = 0
            self.next_frame_time = 0

        async def recv(self) -> AudioFrame:
            if self.start_time is None:
                self.start_time = time.time()

            pts = self.parent.audio_pts
            time_base = self.parent.audio_time_base
            self.parent.audio_pts += SAMPLES_PER_FRAME
            
            # Calculate precise timing for audio frame delivery
            current_time = time.time()
            expected_time = self.start_time + (pts / AUDIO_SAMPLE_RATE)
            
            if expected_time > current_time:
                await asyncio.sleep(expected_time - current_time)

            if len(self.parent.audio_buffer) >= CHUNK_SIZE:
                chunk = self.parent.audio_buffer[:CHUNK_SIZE]
                self.parent.audio_buffer = self.parent.audio_buffer[CHUNK_SIZE:]
                data = np.frombuffer(chunk, dtype=np.int16).reshape(-1, 1)
                frame = AudioFrame.from_ndarray(data.T, format="s16", layout="mono")
            else:
                frame = AudioFrame(format="s16", layout="mono", samples=SAMPLES_PER_FRAME)
                for p in frame.planes:
                    p.update(bytes(p.buffer_size))

            frame.pts = pts
            frame.time_base = time_base
            frame.sample_rate = AUDIO_SAMPLE_RATE
            self.last_pts = pts
            return frame

    class VideoWrapper(CustomVideoTrack):
        kind = "video"
        readyState = "live"

        def __init__(self, parent:'SynchronizedMediaTrack'):
            super().__init__()
            self.parent = parent
            self.start_time = None
            self.frame_duration = 1 / self.parent.fps

        async def recv(self) -> VideoFrame:
            if self.start_time is None:
                self.start_time = time.time()
                
            # Calculate precise timing for this frame
            frame_idx = self.parent.video_frame_index
            expected_time = self.start_time + (frame_idx * self.frame_duration)
            current_time = time.time()
            
            if expected_time > current_time:
                await asyncio.sleep(expected_time - current_time)

            # When param list is exhausted, generate new ones
            if self.parent.param_index >= len(self.parent.param_list):
                audio_data = bytearray()
                try:
                    while len(audio_data) < 32000:
                        try:
                            chunk = await asyncio.wait_for(self.parent.queue.get(), 0.1)
                            audio_data += chunk
                        except asyncio.TimeoutError:
                            if self.parent.current_speech_ended and self.parent.queue.empty():
                                break
                
                    if audio_data:
                        self.parent.param_list = self.parent.avatar.audio2param(audio_data)
                        self.parent.param_index = 0
                except Exception as e:
                    if not self.parent.param_list:
                        self.parent.param_list = [self.parent.avatar.get_idle_param()]
                    
            if self.parent.param_index < len(self.parent.param_list):
                param = self.parent.param_list[self.parent.param_index]
                self.parent.param_index += 1
            else:
                param = self.parent.avatar.get_idle_param()

            frame_id = self.parent.video_frame_index % self.parent.avatar.bg_video_frame_count
            mouth = self.parent.avatar.param2img(param, frame_id)
            frame_img, _ = self.parent.avatar.merge_mouth_to_bg(mouth, frame_id)

            frame = VideoFrame.from_ndarray(frame_img, format="bgr24")
            frame.pts = self.parent.video_frame_index
            frame.time_base = self.parent.video_time_base
            self.parent.video_frame_index += 1
            return frame