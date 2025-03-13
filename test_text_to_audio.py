import asyncio
import base64
import json
import os
import pyaudio
import shutil
import websockets

URI = "wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview-2024-12-17"
SYSTEM_PROMPT = """
Your name is Tao Ye. You speak quickly so that user can understand what you are saying.
You can speak English and Chinese very well. You are bitchy in a sense that you sounds toxic but with good intention.

# Knowledge:            
JANSON Tao, who's an ml engineer at aisera. He's your boyfriend
"""

class AudioStreamer:
    def __init__(self):
        self.audio_engine = pyaudio.PyAudio()
        self.audio_speaker = self.audio_engine.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=24000,
            output=True,
        )

    async def send_text_input(self, ws):
        msg = input("Enter a message: ")
        await ws.send(
            json.dumps(
                {
                    "type": "conversation.item.create",
                    "item": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": msg}],
                    },
                }
            )
        )
        await ws.send(json.dumps({"type": "response.create"}))


    async def send_session_update(self, ws):
        session_config = {
            "modalities": ["audio", "text"],
            "instructions": SYSTEM_PROMPT,
            "voice": "alloy",
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "turn_detection": None,
            "input_audio_transcription": {
                "model": "whisper-1"
            },
            "temperature": 0.6
        }
        session = {
            "type": "session.update",
            "session": session_config
        }
        await ws.send(json.dumps(session))


    async def receive_and_stream(self):
        async with websockets.connect(
            uri=URI,
            extra_headers={
                "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                "OpenAI-Beta": "realtime=v1",
            },
        ) as ws:
            await self.send_session_update(ws) # initialize the setup session.

            async for msg in ws:
                # print as much of the raw event as will fit on the terminal
                columns, rows = shutil.get_terminal_size()
                maxl = columns - 5
                print(msg if len(msg) <= maxl else (msg[:maxl] + " ..."))

                # Event handler
                evt = json.loads(msg)
                if evt["type"] == "session.created":
                    print("session created.")
                    print(json.dumps(evt, indent=2))
                    await self.send_text_input(ws)
                elif evt["type"] == "response.done":
                    await self.send_text_input(ws)
                elif evt["type"] == "conversation.created":
                    pass
                elif evt["type"] == "response.audio.delta":
                    # audio to play
                    audio = base64.b64decode(evt["delta"])
                    self.audio_speaker.write(audio)
                elif evt["type"] == "response.text":
                    # this event does not seem to be sent
                    print(f"> {evt['text']}")
                elif evt["type"] == "response.audio_transcript.delta":
                    pass
                    # print(evt["delta"])
                elif evt["type"] == "response.output_item.done":
                    print(json.dumps(evt, indent=2))
                elif evt["type"] == "error":
                    print(json.dumps(evt, indent=2))

    async def run(self):
        asyncio.create_task(self.receive_and_stream())
        await asyncio.sleep(15 * 60)


if __name__ == "__main__":
    audio_streamer = AudioStreamer()
    asyncio.run(audio_streamer.run())
