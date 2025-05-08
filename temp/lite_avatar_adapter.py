from lite_avatar import liteAvatar
from loguru import logger
import numpy as np
import cv2

class LiteAvatarAdapter:
    def __init__(self, data_dir: str):
        self.model = liteAvatar(data_dir=data_dir, generate_offline=False)
        self.model.load_dynamic_model(data_dir)
        self.bg_frame_count = self.model.bg_video_frame_count
        logger.info(f"Loaded avatar with {self.bg_frame_count} background frames")

    def generate_initial_frames(self, audio_bytes: bytes, count: int = 30):
        param_list = self.model.audio2param(audio_bytes)
        frame_images = []
        for i, param in enumerate(param_list[:count]):
            frame_id = i % self.bg_frame_count
            mouth = self.model.param2img(param, frame_id)
            full_img, _ = self.model.merge_mouth_to_bg(mouth, frame_id)
            frame_images.append(full_img)
        logger.info(f"Generated {len(frame_images)} video frames for first {count} audio frames.")
        return frame_images, len(param_list)
