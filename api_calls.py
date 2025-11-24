import asyncio
import base64
import datetime
import json
import os

import aiohttp
import requests
import websockets
from gtts import gTTS
from livekit.api import VideoGrants
from livekit.api.access_token import AccessToken
from livekit.api.room_service import RoomService
from livekit.protocol.room import CreateRoomRequest
from pydub import AudioSegment

# Configuration - replace with your actual keys and IDs
LIVEKIT_URL = "wss://livekit.mayflower.cloud" # Change me
LIVEKIT_API_KEY = "<YOUR_LIVEKIT_API_KEY>"
LIVEKIT_API_SECRET = "<YOUR_LIVEKIT_API_SECRET>"
LIVEKIT_ROOM_NAME = "liveavatar-test-room"
LIVEAVATAR_API_KEY = "<YOUR_LIVEAVATAR_API_KEY>"
LIVEAVATAR_AVATAR_ID = "e9844e6d-847e-4964-a92b-7ecd066f69df"
LIVEAVATAR_IDENTITY = "liveavatar-avatar"
LIVEAVATAR_NAME = "LiveAvatar"

liveavatar_session_id = ""
liveavatar_session_token = ""
liveavatar_ws_url = ""

# 1. Create the room via RoomService
async def create_room():
    async with aiohttp.ClientSession() as http_session:
        room_service = RoomService(
            session=http_session,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET,
            url=LIVEKIT_URL,
        )

        # Create room request with name and metadata
        create_room_request = CreateRoomRequest()
        create_room_request.name = LIVEKIT_ROOM_NAME

        await room_service.create_room(create_room_request)

asyncio.run(create_room())
print("LiveKit room created.")

# 2. Create LiveAvatar session token

# Generate LiveKit token for LiveAvatar
token = (
    AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    .with_identity(LIVEAVATAR_IDENTITY)
    .with_name(LIVEAVATAR_NAME)
    .with_ttl(datetime.timedelta(minutes=10))
    .with_grants(
        VideoGrants(
            room_join=True,
            room=LIVEKIT_ROOM_NAME,
            can_subscribe=True,
            can_publish=True,
            can_publish_data=True,
        )
    )
    .to_jwt()
)
print(f"Generated LiveKit token: {token}")

url = "https://api.liveavatar.com/v1/sessions/token"

payload = {
    "avatar_id": LIVEAVATAR_AVATAR_ID,
    "mode": "CUSTOM",
    "livekit_config": {
        "livekit_url": LIVEKIT_URL,
        "livekit_room": LIVEKIT_ROOM_NAME,
        "livekit_client_token": token,
    },
}
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "X-API-KEY": LIVEAVATAR_API_KEY,
}

print("Creating LiveAvatar session token...")
response = requests.post(url, json=payload, headers=headers, timeout=10)
response_data = response.json()
print(response_data)

data = response_data.get("data", {})
session_id = data.get("session_id")
session_token = data.get("session_token")
print(f"Session ID: {session_id}")
print(f"Session Token: {session_token}")
print("LiveAvatar session token created.")

# 3. Start LiveAvatar session

url = "https://api.liveavatar.com/v1/sessions/start"

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": f"Bearer {session_token}",
}

print("Starting LiveAvatar session...")
response = requests.post(url, headers=headers, timeout=10)
print(response.json())
ws_url = response.json().get("data", {}).get("ws_url")

print(f"WebSocket URL: {ws_url}")
print("LiveAvatar session started.")

# 4. Send audio data via WebSocket

async def send_german_audio_to_liveavatar():
    """Generate German audio and stream it to LiveAvatar WebSocket"""
    # Define persistent audio file path
    audio_file_path = "german_greeting.mp3"

    # Check if audio file already exists, if not generate it
    if not os.path.exists(audio_file_path):
        print(
            "Generating German audio: 'Hallo wie geht es Ihnen heute' (first time)..."
        )
        # Generate German speech using gTTS
        tts = gTTS(text="Hallo wie geht es Ihnen heute", lang="de", slow=False)
        tts.save(audio_file_path)
        print(f"Audio saved to: {audio_file_path}")
    else:
        print(f"Using existing audio file: {audio_file_path}")

    # Load audio with pydub and convert to required format
    # LiveAvatar requires: PCM 16-bit, 24kHz, mono
    audio = AudioSegment.from_mp3(audio_file_path)

    # Convert to mono
    audio = audio.set_channels(1)

    # Convert to 24kHz sample rate
    audio = audio.set_frame_rate(24000)

    # Convert to 16-bit PCM
    audio = audio.set_sample_width(2)  # 2 bytes = 16 bits

    print(
        f"Audio converted to format: {audio.frame_rate}Hz, "
        f"{audio.channels} channel(s), {audio.sample_width * 8}-bit"
    )

    # Get raw PCM data
    pcm_data = audio.raw_data

    # Split audio into chunks (similar to how frames are sent in avatar.py)
    # Each chunk represents approximately 20ms of audio at 24kHz
    # 24000 samples/sec * 0.02 sec = 480 samples per chunk
    # 480 samples * 2 bytes = 960 bytes per chunk
    chunk_size = 960
    event_id_counter = 0

    print(
        f"Streaming {len(pcm_data)} bytes of audio in {chunk_size}-byte chunks..."
    )

    # Connect to websocket
    async with websockets.connect(ws_url) as ws:
        print("Connected to LiveAvatar WebSocket for audio streaming")

        # Stream audio chunks
        for i in range(0, len(pcm_data), chunk_size):
            chunk = pcm_data[i : i + chunk_size]

            # Skip empty chunks
            if not chunk:
                continue

            # Encode as base64
            audio_b64 = base64.b64encode(chunk).decode("utf-8")

            # Send to LiveAvatar with correct format per API documentation
            message = {
                "type": "agent.speak",
                "event_id": str(event_id_counter),
                "audio": audio_b64,
            }

            await ws.send(json.dumps(message))
            event_id_counter += 1

            # Small delay to simulate real-time streaming
            await asyncio.sleep(0.02)  # 20ms per chunk

        print(f"Sent {event_id_counter} audio chunks to LiveAvatar")

        # Send speak_end signal
        await ws.send(json.dumps({"type": "agent.speak_end"}))
        print("Sent agent.speak_end signal")

        # Wait a bit to receive any response events
        print("Listening for LiveAvatar events...")
        try:
            async with asyncio.timeout(10):  # Wait up to 10 seconds for events
                async for message in ws:
                    print(f"Received event: {message}")
                    data = (
                        json.loads(message) if isinstance(message, str) else message
                    )
                    event_type = data.get("type", "<none>")

                    # Stop listening after avatar finishes speaking
                    if event_type == "agent.speak_ended":
                        print("Avatar finished speaking")
                        break
        except asyncio.TimeoutError:
            print("Timeout waiting for avatar events")

# Run the audio streaming function
asyncio.run(send_german_audio_to_liveavatar())
print("Finished streaming audio to LiveAvatar")

# 5. Stop LiveAvatar session

url = "https://api.liveavatar.com/v1/sessions/stop"

payload = {
    "session_id": session_id,
}

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "x-api-key": LIVEAVATAR_API_KEY,
}

print(f"Stopping LiveAvatar session: {session_id}...")
response = requests.post(url, headers=headers, json=payload)
print(response.json())
print("LiveAvatar session stopped.")
