import os
import asyncio
import cv2
import wave
from dotenv import load_dotenv
from lite_avatar import liteAvatar
from modules.elevenlabs.client import ElevenLabs
from modules.elevenlabs.types.voice_settings import VoiceSettings
from modules.elevenlabs.core.request_options import RequestOptions

load_dotenv()

TEXT_INPUT = "Hello there! This is a real-time demonstration of a synthetic voice and animated avatar working together. We're testing lip movements, frame alignment, and sentence pacing. Can you see the avatar respond as each word is spoken? Synchronization is critical in applications like virtual meetings, AI agents, and interactive presentations."


OUTPUT_DIR = "./output_video"
AUDIO_PATH = os.path.join(OUTPUT_DIR, "output.wav")
VIDEO_DIR = os.path.join(OUTPUT_DIR, "frames")
FINAL_VIDEO_PATH = os.path.join(OUTPUT_DIR, "avatar_output.mp4")

os.makedirs(VIDEO_DIR, exist_ok=True)

# 🧠 Avatar processor
avatar = liteAvatar(data_dir="./data/preload", generate_offline=True, use_gpu=False, fps=30)

# 🎤 ElevenLabs TTS
tts_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

async def synthesize_audio_with_elevenlabs() -> bytes:
    audio_chunks = tts_client.generate(
        text=TEXT_INPUT,
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
        request_options=RequestOptions(timeout_in_seconds=300),
    )

    audio_bytes = bytearray()
    for chunk in audio_chunks:
        audio_bytes.extend(chunk)

    # Save WAV
    with wave.open(AUDIO_PATH, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(audio_bytes)

    return bytes(audio_bytes)

def generate_video_frames(audio_bytes: bytes):
    param_list = avatar.audio2param(audio_bytes)
    for i, param in enumerate(param_list):
        frame_id = i % avatar.bg_video_frame_count
        mouth = avatar.param2img(param, frame_id)
        frame, _ = avatar.merge_mouth_to_bg(mouth, frame_id)
        path = os.path.join(VIDEO_DIR, f"{str(i+1).zfill(5)}.jpg")
        cv2.imwrite(path, frame)

async def main():
    audio_bytes = await synthesize_audio_with_elevenlabs()
    generate_video_frames(audio_bytes)

    # 🎞️ Merge video and audio
    cmd = f"ffmpeg -y -r 30 -i {VIDEO_DIR}/%05d.jpg -i {AUDIO_PATH} -c:v libx264 -pix_fmt yuv420p -b:v 5000k {FINAL_VIDEO_PATH}"
    os.system(cmd)
    print(f"✅ Final video saved: {FINAL_VIDEO_PATH}")

if __name__ == "__main__":
    asyncio.run(main())
