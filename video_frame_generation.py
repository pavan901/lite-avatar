from avatar_image_processor import AvatarImageProcessor

def generate_video_frames_from_audio(audio_bytes, queue, data_path):
    print("[Subprocess] Initializing Avatar and generating frames...")
    processor = AvatarImageProcessor(data_dir=data_path)

    param_list = processor.avatar.audio2param(audio_bytes)

    for i, param in enumerate(param_list):
        frame_id = i % processor.avatar.bg_video_frame_count
        mouth = processor.avatar.param2img(param, frame_id)
        frame_img, _ = processor.avatar.merge_mouth_to_bg(mouth, frame_id)
        queue.put(frame_img)
        print(f"[Subprocess] Frame {i} pushed")
