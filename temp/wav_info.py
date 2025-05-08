import wave

def get_wav_info(file_path):
    with wave.open(file_path, 'rb') as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        frame_rate = wav_file.getframerate()
        num_frames = wav_file.getnframes()
        duration = num_frames / float(frame_rate)
        
        return {
            'channels': channels,
            'sample_width': sample_width,
            'frame_rate': frame_rate,
            'num_frames': num_frames,
            'duration': duration
        }


wav_info = get_wav_info("abcd.wav")

print(f"Channels: {wav_info['channels']}")
print(f"Sample Width: {wav_info['sample_width']} bytes")
print(f"Frame Rate: {wav_info['frame_rate']} Hz")
print(f"Number of Frames: {wav_info['num_frames']}")
print(f"Duration: {wav_info['duration']} seconds")