from avatar_image_processor import AvatarImageProcessor
from queue import Full
from concurrent.futures import ThreadPoolExecutor

def generate_video_frames_from_audio(audio_bytes, queue, data_path, ready_event):
    processor = AvatarImageProcessor(data_dir=data_path)
    param_list = processor.avatar.audio2param(audio_bytes)
    total = len(param_list)
    half = total // 2

    def render_and_queue(i_param):
        i, param = i_param
        frame_id = i % processor.avatar.bg_video_frame_count
        mouth = processor.avatar.param2img(param, frame_id)
        frame_img, _ = processor.avatar.merge_mouth_to_bg(mouth, frame_id)
        try:
            queue.put(frame_img, timeout=1)
        except Full:
            print(f"[Subprocess] Queue full at frame {i}, skipping.")
        if i + 1 == half:
            print(f"[Subprocess] {half} frames generated. Signaling ready.")
            ready_event.set()

    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.map(render_and_queue, enumerate(param_list))
