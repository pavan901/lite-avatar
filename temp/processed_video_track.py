import asyncio
from fractions import Fraction
from typing import Awaitable, Callable, Optional
from av import VideoFrame
from videosdk import CustomVideoTrack
from avatar_image_processor import AvatarImageProcessor

class ProcessedVideoTrack(CustomVideoTrack):
    kind = "video"

    def __init__(self, processor: AvatarImageProcessor, fps=30):
        super().__init__()
        self.processor = processor
        self.fps = fps
        self.last_frame_time = None
        self.frame_counter = 0
        self.should_call_play_lip_sync = False
        self.play_lip_sync: Optional[Callable[[], Awaitable[None]]] = None

    async def recv(self) -> VideoFrame:
        # ⏱️ Maintain frame rate
        if self.last_frame_time:
            delay = (1 / self.fps) - (asyncio.get_event_loop().time() - self.last_frame_time)
            if delay > 0:
                await asyncio.sleep(delay)
        self.last_frame_time = asyncio.get_event_loop().time()

        try:
            # 🧠 Param generation
            if self.processor.queue.empty() and self.processor.param_index >= len(self.processor.param_list):
                param = self.processor.idle_param
                self.should_call_play_lip_sync = True
            else:
                if self.processor.param_index >= len(self.processor.param_list):
                    required_bytes = 32000  # 1 second of 16kHz mono PCM @ 16-bit
                    audio_buffer = bytearray()

                    # ⏳ Accumulate enough audio from TTS
                    while len(audio_buffer) < required_bytes:
                        chunk = await self.processor.queue.get()
                        if chunk:
                            audio_buffer += chunk

                    # 🧼 Trim to multiple of 32000 bytes to avoid ONNX errors
                    if len(audio_buffer) % required_bytes != 0:
                        trim_len = len(audio_buffer) - (len(audio_buffer) % required_bytes)
                        audio_buffer = audio_buffer[:trim_len]

                    if len(audio_buffer) < required_bytes:
                        raise ValueError("Insufficient audio collected for avatar model.")

                    self.processor.param_list = self.processor.avatar.audio2param(audio_buffer)
                    self.processor.param_index = 0

                param = self.processor.param_list[self.processor.param_index]
                self.processor.param_index += 1

            # 🎨 Generate frame from param
            frame_id = self.frame_counter % self.processor.avatar.bg_video_frame_count
            mouth = self.processor.avatar.param2img(param, frame_id)
            frame_img, _ = self.processor.avatar.merge_mouth_to_bg(mouth, frame_id)
            if (self.should_call_play_lip_sync) and (self.play_lip_sync is not None):
                self.play_lip_sync()
                self.should_call_play_lip_sync = False

        except Exception as e:
            print(f"[ProcessedVideoTrack] Error generating avatar frame: {e}")
            mouth = self.processor.avatar.param2img(self.processor.idle_param, 0)
            frame_img, _ = self.processor.avatar.merge_mouth_to_bg(mouth, 0)

        # 📦 Package frame
        frame = VideoFrame.from_ndarray(frame_img, format="bgr24")
        frame.pts = self.frame_counter
        frame.time_base = Fraction(1, self.fps)
        self.frame_counter += 1

        return frame

    # async def recv(self) -> VideoFrame:
    #     print("[Video] Waiting for frame from synchronized queue...")
    #     try:
    #         # Wait for one AV tuple from the synchronized queue
    #         _, _, _, video_frame = await synchronized_av_queue.get()
    #         print("[Video] Pulled 1 frame from queue.")
    #         return video_frame
    #     except Exception as e:
    #         print("[Video Error]:", e)
    #         # fallback: blank frame
    #         frame_id = 0
    #         mouth = self.processor.avatar.param2img(self.processor.idle_param, frame_id)
    #         frame_img, _ = self.processor.avatar.merge_mouth_to_bg(mouth, frame_id)
    #         fallback_frame = VideoFrame.from_ndarray(frame_img, format="bgr24")
    #         fallback_frame.pts = 0
    #         fallback_frame.time_base = Fraction(1, self.fps)
    #         return fallback_frame
