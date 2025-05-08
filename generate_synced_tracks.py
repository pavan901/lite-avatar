import time
from multiprocessing import Queue, Event, Process
from modules.elevenlabs.client import ElevenLabs
from modules.elevenlabs.types.voice_settings import VoiceSettings
from modules.elevenlabs.core.request_options import RequestOptions
from generate_video_frames import generate_video_frames_from_audio
from playback import PreRenderedAudioTrack, StreamingVideoTrack

def generate_synced_tracks(text, api_key, data_path):
    print("[Main] Generating audio...")
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

    video_queue = Queue(maxsize=100)
    ready_event = Event()
    start_time = time.time() + 1.0  # buffer for sync

    process = Process(
        target=generate_video_frames_from_audio,
        args=(audio_bytes, video_queue, data_path, ready_event)
    )
    process.start()

    audio_track = PreRenderedAudioTrack(audio_bytes, start_time)
    video_track = StreamingVideoTrack(video_queue, fps=30, ready_event=ready_event, start_time=start_time)

    return audio_track, video_track
