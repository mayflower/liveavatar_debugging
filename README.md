# liveavatar_debugging

Testing and debugging LiveAvatar integration with LiveKit.

## Prerequisites

- Python 3.12 or higher
- ffmpeg (required by pydub for audio processing)

### Installing ffmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html)

## Setup

1. Install dependencies using uv (recommended):

   ```bash
   uv sync
   ```

   This will create a virtual environment and install all dependencies from [pyproject.toml](pyproject.toml).

2. Configure API credentials in [api_calls.py](api_calls.py):

   Update the following variables at the top of the file (lines 18-25):
   ```python
   LIVEKIT_URL = "wss://livekit.mayflower.cloud"
   LIVEKIT_API_KEY = "<YOUR_LIVEKIT_API_KEY>"
   LIVEKIT_API_SECRET = "<YOUR_LIVEKIT_API_SECRET>"
   LIVEKIT_ROOM_NAME = "liveavatar-test-room"
   LIVEAVATAR_API_KEY = "<YOUR_LIVEAVATAR_API_KEY>"
   LIVEAVATAR_AVATAR_ID = "e9844e6d-847e-4964-a92b-7ecd066f69df"
   LIVEAVATAR_IDENTITY = "liveavatar-avatar"
   LIVEAVATAR_NAME = "LiveAvatar"
   ```

## Running the Script

Execute the script using uv to test the full LiveAvatar workflow:

```bash
uv run api_calls.py
```

This automatically runs the script in the uv-managed virtual environment.

## What the Script Does

The [api_calls.py](api_calls.py) script performs the following steps:

1. **Creates a LiveKit room** using the LiveKit RoomService API
2. **Generates a LiveKit token** for the LiveAvatar participant
3. **Creates a LiveAvatar session** using the LiveKit room and token
4. **Starts the LiveAvatar session** and receives a WebSocket URL
5. **Generates German audio** ("Hallo wie geht es Ihnen heute") using Google TTS
6. **Converts audio** to the required format (PCM 16-bit, 24kHz, mono)
7. **Streams audio** to LiveAvatar via WebSocket in 20ms chunks
8. **Listens for events** from LiveAvatar (e.g., when the avatar finishes speaking)
9. **Stops the LiveAvatar session** when complete

## Output

The script will:
- Create a cached audio file `german_greeting.mp3` (reused on subsequent runs)
- Print status messages for each step
- Display LiveAvatar session details (session ID, token, WebSocket URL)
- Show real-time events from the LiveAvatar WebSocket

## Troubleshooting

- **Missing ffmpeg**: If you get an error about audio conversion, make sure ffmpeg is installed
- **API authentication errors**: Verify your API keys are correct in the configuration section
- **WebSocket connection issues**: Check that the LiveKit URL is accessible and correctly formatted
- **Timeout errors**: The script waits up to 10 seconds for LiveAvatar events; increase the timeout if needed
