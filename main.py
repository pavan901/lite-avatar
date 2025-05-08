import asyncio
import os
from dotenv import load_dotenv
from multiprocessing import set_start_method
from videosdk import MeetingConfig, VideoSDK, MeetingEventHandler, ParticipantEventHandler, Stream, Participant, Meeting
from generate_synced_tracks import generate_synced_tracks

# Ensure proper multiprocessing context
set_start_method("spawn", force=True)

# Load environment variables
load_dotenv()
TEXT = "Hello everyone! I’m an AI avatar ready to talk in real time."
TOKEN = os.getenv("VIDEOSDK_TOKEN")
MEETING_ID = "your-meeting-id"
NAME = os.getenv("NAME")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
AVATAR_DATA_PATH = "./data/preload"

# Define meeting event handlers
class MyMeetingEventHandler(MeetingEventHandler):
    def on_meeting_left(self, data):
        print("Meeting left:", data)

    def on_participant_joined(self, participant: Participant):
        print(f"Participant joined: {participant.id}")
        participant.add_event_listener(MyParticipantEventHandler(participant.id))

    def on_participant_left(self, participant: Participant):
        print(f"Participant left: {participant.id}")

class MyParticipantEventHandler(ParticipantEventHandler):
    def __init__(self, participant_id: str):
        super().__init__()
        self.participant_id = participant_id

    def on_stream_enabled(self, stream: Stream):
        print(f"Stream enabled: {stream.kind} by {self.participant_id}")

    def on_stream_disabled(self, stream: Stream):
        print(f"Stream disabled by {self.participant_id}")

# Main function with debug tracing
def main():
    print("DEBUG: Entered main()")

    print("DEBUG: Calling generate_synced_tracks()")
    audio_track, video_track = generate_synced_tracks(TEXT, ELEVENLABS_API_KEY, AVATAR_DATA_PATH)
    print("DEBUG: Tracks generated")

    print("DEBUG: Initializing meeting")
    config = MeetingConfig(
        meeting_id=MEETING_ID,
        name=NAME,
        mic_enabled=True,
        webcam_enabled=True,
        token=TOKEN,
        custom_camera_video_track=video_track,
        custom_microphone_audio_track=audio_track,
    )

    try:
        meeting: Meeting = VideoSDK.init_meeting(**config)
        print("DEBUG: Meeting initialized")
        meeting.add_event_listener(MyMeetingEventHandler())
        print("DEBUG: Listener added")
        meeting.join()
        print("DEBUG: Meeting joined")
    except Exception as e:
        print(f"[ERROR] Failed to initialize or join meeting: {e}")

if __name__ == "__main__":
    print("DEBUG: Starting main()")
    main()
    print("DEBUG: Entering asyncio loop")
    asyncio.get_event_loop().run_forever()
