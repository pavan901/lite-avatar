# import time
# import numpy as np
# from modules.elevenlabs.client import ElevenLabs
# from modules.elevenlabs.types.voice_settings import VoiceSettings
# from modules.elevenlabs.core.request_options import RequestOptions
# from avatar_image_processor import AvatarImageProcessor
# from playback import PreRenderedAudioTrack, PreRenderedVideoTrack

# def batch_params(param_list, batch_size=30):
#     batches = []
#     total = len(param_list)
#     for i in range(0, total, batch_size):
#         batches.append(param_list[i:i + batch_size])
#     return batches

# def generate_synced_tracks(text, api_key, avatar_data_path):
#     print("Generating speech and animation...")

#     # ---------- Audio Generation ----------
#     t_start_audio = time.time()
#     tts = ElevenLabs(api_key=api_key)
#     audio_bytes = b''.join(tts.generate(
#         text=text,
#         stream=True,
#         output_format="pcm_16000",
#         model="eleven_multilingual_v2",
#         voice="EXAVITQu4vr4xnSDxMaL",
#         voice_settings=VoiceSettings(
#             stability=0.71,
#             similarity_boost=0.5,
#             style=0.0,
#             use_speaker_boost=True,
#         ),
#         request_options=RequestOptions(timeout_in_seconds=300)
#     ))
#     t_audio = time.time() - t_start_audio
#     print(f"Audio generated in {t_audio:.2f}s.")

#     # ---------- Param Generation ----------
#     processor = AvatarImageProcessor(data_dir=avatar_data_path)
#     t_start_param = time.time()
#     param_list = processor.avatar.audio2param(audio_bytes)
#     t_param = time.time() - t_start_param
#     print(f"Generated {len(param_list)} param frames in {t_param:.2f}s.")

#     # ---------- Batched Video Frame Generation ----------
#     batches = batch_params(param_list, 30)
#     print(f"Processing {len(batches)} batches...")
#     video_images = []

#     total_video_start = time.time()
#     for i, batch in enumerate(batches):
#         batch_start = time.time()
#         for j, param in enumerate(batch):
#             frame_id = (i * 30 + j) % processor.avatar.bg_video_frame_count
#             mouth = processor.avatar.param2img(param, frame_id)
#             frame_img, _ = processor.avatar.merge_mouth_to_bg(mouth, frame_id)
#             video_images.append(frame_img)
#         batch_duration = time.time() - batch_start
#         print(f"Batch {i + 1}/{len(batches)}: {len(batch)} frames generated in {batch_duration:.2f}s")

#     total_video_time = time.time() - total_video_start
#     print(f"Total video generation time: {total_video_time:.2f}s")
#     print(f"Overall processing time: {t_audio + t_param + total_video_time:.2f}s\n")

#     # ---------- Create Tracks ----------
#     audio_track = PreRenderedAudioTrack(audio_bytes)
#     video_track = PreRenderedVideoTrack(video_images, fps=30)
#     return audio_track, video_track



# multi threading version
# import time
# import numpy as np
# from concurrent.futures import ThreadPoolExecutor, as_completed

# from modules.elevenlabs.client import ElevenLabs
# from modules.elevenlabs.types.voice_settings import VoiceSettings
# from modules.elevenlabs.core.request_options import RequestOptions

# from avatar_image_processor import AvatarImageProcessor
# from playback import PreRenderedAudioTrack, PreRenderedVideoTrack

# MAX_THREADS = 8 
# BATCH_SIZE = 30

# def batch_params(param_list, batch_size=BATCH_SIZE):
#     batches = []
#     total = len(param_list)
#     for i in range(0, total, batch_size):
#         batches.append(param_list[i:i+batch_size])
#     return batches

# def process_batch(batch_index, batch,  processor : AvatarImageProcessor):
#     start = time.time()
#     frames = []
#     for j, param in enumerate(batch):
#         frame_id = (batch_index * BATCH_SIZE + j) % processor.avatar.bg_video_frame_count
#         mouth = processor.avatar.param2img(param, frame_id)
#         frame_img, _ = processor.avatar.merge_mouth_to_bg(mouth, frame_id)
#         frames.append(frame_img)
#     end = time.time()
#     print(f"Batch {batch_index + 1}: {len(batch)} frames generated in {end - start:.2f}s")
#     return batch_index, frames

# def generate_synced_tracks(text, api_key, avatar_data_path):
#     print("Generating speech and animation...")
#     tts = ElevenLabs(api_key=api_key)

#     start_time = time.time()
#     audio_bytes = b''.join(tts.generate(
#         text=text,
#         stream=True,
#         output_format="pcm_16000",
#         model="eleven_multilingual_v2",
#         voice="EXAVITQu4vr4xnSDxMaL",
#         voice_settings=VoiceSettings(
#             stability=0.71,
#             similarity_boost=0.5,
#             style=0.0,
#             use_speaker_boost=True,
#         ),
#         request_options=RequestOptions(timeout_in_seconds=300)
#     ))
#     print(f"Audio generated in {time.time() - start_time:.2f}s.")

#     processor = AvatarImageProcessor(data_dir=avatar_data_path)

#     start = time.time()
#     param_list = processor.avatar.audio2param(audio_bytes)
#     print(f"Generated {len(param_list)} param frames in {time.time() - start:.2f}s.")

#     batches = batch_params(param_list)
#     print(f"Processing {len(batches)} batches with multithreading...")

#     video_images = [None] * len(param_list)
#     start = time.time()

#     with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
#         futures = {executor.submit(process_batch, idx, batch, processor): idx for idx, batch in enumerate(batches)}
#         for future in as_completed(futures):
#             batch_idx, batch_frames = future.result()
#             for j, frame in enumerate(batch_frames):
#                 global_idx = batch_idx * BATCH_SIZE + j
#                 video_images[global_idx] = frame

#     print(f"Total video generation time: {time.time() - start:.2f}s")
#     print(f"Overall processing time: {time.time() - start_time:.2f}s")

#     audio_track = PreRenderedAudioTrack(audio_bytes)
#     video_track = PreRenderedVideoTrack(video_images, fps=30)
#     return audio_track, video_track

# Multi Processing version

# import time
# import multiprocessing
# from modules.elevenlabs.client import ElevenLabs
# from modules.elevenlabs.types.voice_settings import VoiceSettings
# from modules.elevenlabs.core.request_options import RequestOptions

# from avatar_image_processor import AvatarImageProcessor
# from playback import PreRenderedAudioTrack, PreRenderedVideoTrack

# BATCH_SIZE = 30

# def batch_params(param_list, batch_size=BATCH_SIZE):
#     return [param_list[i:i+batch_size] for i in range(0, len(param_list), batch_size)]

# def process_batch_multiprocessing(args):
#     batch_index, batch, avatar_data_path = args
#     processor = AvatarImageProcessor(data_dir=avatar_data_path)
#     start = time.time()
#     frames = []
#     for j, param in enumerate(batch):
#         frame_id = (batch_index * BATCH_SIZE + j) % processor.avatar.bg_video_frame_count
#         mouth = processor.avatar.param2img(param, frame_id)
#         frame_img, _ = processor.avatar.merge_mouth_to_bg(mouth, frame_id)
#         frames.append(frame_img)
#     print(f"Batch {batch_index + 1}: {len(batch)} frames generated in {time.time() - start:.2f}s")
#     return batch_index, frames

# def generate_synced_tracks(text, api_key, avatar_data_path):
#     print("Generating speech and animation...")
#     tts = ElevenLabs(api_key=api_key)

#     start_time = time.time()
#     audio_bytes = b''.join(tts.generate(
#         text=text,
#         stream=True,
#         output_format="pcm_16000",
#         model="eleven_multilingual_v2",
#         voice="EXAVITQu4vr4xnSDxMaL",
#         voice_settings=VoiceSettings(
#             stability=0.71,
#             similarity_boost=0.5,
#             style=0.0,
#             use_speaker_boost=True,
#         ),
#         request_options=RequestOptions(timeout_in_seconds=300)
#     ))
#     print(f"Audio generated in {time.time() - start_time:.2f}s.")

#     dummy_processor = AvatarImageProcessor(data_dir=avatar_data_path)
#     param_list = dummy_processor.avatar.audio2param(audio_bytes)
#     print(f"Generated {len(param_list)} param frames.")

#     batches = batch_params(param_list)
#     print(f"Processing {len(batches)} batches using multiprocessing...")

#     video_images = [None] * len(param_list)
#     args = [(i, batch, avatar_data_path) for i, batch in enumerate(batches)]

#     start = time.time()
#     with multiprocessing.Pool(processes=min(multiprocessing.cpu_count(), len(batches))) as pool:
#         results = pool.map(process_batch_multiprocessing, args)

#     for batch_idx, batch_frames in results:
#         for j, frame in enumerate(batch_frames):
#             global_idx = batch_idx * BATCH_SIZE + j
#             video_images[global_idx] = frame

#     print(f"Total video generation time: {time.time() - start:.2f}s")
#     print(f"Overall processing time: {time.time() - start_time:.2f}s")

#     return PreRenderedAudioTrack(audio_bytes), PreRenderedVideoTrack(video_images, fps=30)

from multiprocessing import Queue, Process
from modules.elevenlabs.client import ElevenLabs
from modules.elevenlabs.types.voice_settings import VoiceSettings
from modules.elevenlabs.core.request_options import RequestOptions
from video_frame_generation import generate_video_frames_from_audio
from playback import PreRenderedAudioTrack, StreamingVideoTrack

SAMPLES_PER_FRAME = 320  # 20ms per frame

def generate_synced_tracks(text, api_key, avatar_data_path):
    print("Generating audio...")
    tts = ElevenLabs(api_key=api_key)
    audio_bytes = b''.join(tts.generate(
        text=text,
        stream=True,
        output_format="pcm_16000",
        model="eleven_multilingual_v2",
        voice="EXAVITQu4vr4xnSDxMaL",
        voice_settings=VoiceSettings(
            stability=0.71,
            similarity_boost=0.5,
            style=0.0,
            use_speaker_boost=True,
        ),
        request_options=RequestOptions(timeout_in_seconds=300)
    ))

    total_audio_frames = len(audio_bytes) 
    half_audio_frames = total_audio_frames // 2
    print(f"Generated {total_audio_frames} audio frames.")

    video_queue = Queue()
    process = Process(
        target=generate_video_frames_from_audio,
        args=(audio_bytes, video_queue, avatar_data_path)
    )
    process.start()

    audio_track = PreRenderedAudioTrack(audio_bytes)
    video_track = StreamingVideoTrack(video_queue, fps=30, wait_for=half_audio_frames)

    return audio_track, video_track
