import json
import os

from textwrap import dedent
from dotenv import load_dotenv
from livekit import agents, rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    RunContext,
    ToolError,
    function_tool,
    inference,
    mcp,
    room_io,
)
from livekit.plugins import noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

load_dotenv(".env.local")


class Assistant(Agent):
    def __init__(self, pinecone_server: mcp.MCPServerStdio) -> None:
        super().__init__(
            instructions=dedent("""\
                You are a helpful voice AI assistant for an interactive video page.
                You eagerly assist users with their questions by providing
                information from your extensive knowledge.
                Your responses are concise, to the point, and without any complex
                formatting or punctuation including emojis, asterisks, or other symbols.

                You are curious, friendly, and have a sense of humor.
                You can fully control the video through tools.
            """),
        )
        self._pinecone = pinecone_server

    async def _rpc(
        self, context: RunContext, method: str, payload: dict | None = None
    ) -> str:
        room_io_ctx = context.session.room_io
        linked_participant = room_io_ctx.linked_participant
        if linked_participant is None:
            raise ToolError("No linked participant is available for video control yet.")

        return await room_io_ctx.room.local_participant.perform_rpc(
            destination_identity=linked_participant.identity,
            method=method,
            payload=json.dumps(payload or {}),
            response_timeout=5.0,
        )

    @function_tool()
    async def search_video_content(self, context: RunContext, query_text: str) -> str:
        """Search the video transcript for relevant segments by topic or keyword.
        Use when the user asks what was said, discussed, or covered in the video.
        Do not use for video playback control.

        Args:
            query_text: A natural-language description of the topic or content to find.
        """
        if self._pinecone._client is None:
            raise ToolError("Search service is not available.")

        result = await self._pinecone._client.call_tool(
            "search-records", {
                "name": "avengers",
                "namespace": "evt_spreadsheet_hacks",
                "query": {
                    "topK": 10,
                    "inputs": {"text": query_text},
                },
            }
        )

        if result.isError:
            error_str = "\n".join(
                part.text if hasattr(part, "text") else str(part)
                for part in result.content
            )
            raise ToolError(error_str)
        if len(result.content) == 1:
            return result.content[0].model_dump_json()
        elif len(result.content) > 1:
            return json.dumps([item.model_dump() for item in result.content])
        return "No results found."

    @function_tool()
    async def play_video(self, context: RunContext) -> str:
        """Resume or start playing the video.
        Use when the user asks to play, resume, or start the video.
        """
        await self._rpc(context, "video.play")
        return "Video is now playing."

    @function_tool()
    async def pause_video(self, context: RunContext) -> str:
        """Pause the video.
        Use when the user asks to pause or stop the video.
        """
        await self._rpc(context, "video.pause")
        return "Video paused."

    @function_tool()
    async def set_video_timestamp(self, context: RunContext, seconds: float) -> None:
        """Jump to an absolute position in the video.
        Use when the user specifies an exact time.
        Do not use for relative seeks — use seek_video_by instead.

        Args:
            seconds: Absolute position from the start of the video in seconds. Must be >= 0.
        """
        if seconds < 0:
            raise ToolError("Timestamp must be 0 seconds or greater.")
        context.disallow_interruptions()
        await self._rpc(context, "video.setCurrentTime", {"time": seconds})

    @function_tool()
    async def seek_video_by(self, context: RunContext, delta: float) -> None:
        """Seek the video by a relative offset in seconds.
        Use when the user says rewind, skip forward, go back, or jump
        forward/backward by N seconds.
        Do not use for jumping to an absolute time — use set_video_timestamp instead.

        Args:
            delta: Offset in seconds. Positive values seek forward, negative
                   values seek backward.
        """
        context.disallow_interruptions()
        await self._rpc(context, "video.seekBy", {"delta": delta})

    @function_tool()
    async def add_video_bookmark(
        self, context: RunContext, label: str = "Bookmark", time: float | None = None
    ) -> str:
        """Save a bookmark at the current or a specified video position.
        Use when the user asks to remember a moment, save a spot, or add a bookmark.

        Args:
            label: A short descriptive label for the bookmark.
            time: Absolute timestamp in seconds to bookmark. Defaults to the
            current playback position.
        """
        payload: dict = {"label": label}
        if time is not None:
            payload["time"] = time
        await self._rpc(context, "video.addBookmark", payload)
        return f"Bookmark '{label}' saved."

    @function_tool()
    async def add_video_note(
        self, context: RunContext, text: str, time: float | None = None
    ) -> str:
        """Save a text note at the current or a specified video position.
        Use when the user asks to write something down, take a note, or
        annotate the video.

        Args:
            text: The content of the note to save.
            time: Absolute timestamp in seconds to attach the note to. Defaults
            to the current playback position.
        """
        payload: dict = {"text": text}
        if time is not None:
            payload["time"] = time
        await self._rpc(context, "video.addNote", payload)
        return "Note saved."


server = AgentServer()


@server.rtc_session(agent_name="eva")
async def my_agent(ctx: agents.JobContext):

    pinecone = mcp.MCPServerStdio(
        command="npx",
        args=["-y", "@pinecone-database/mcp"],
        env={**os.environ, "PINECONE_API_KEY": os.environ["PINECONE_API_TOKEN"]},
    )

    session = AgentSession(
        stt="deepgram/nova-3:multi",
        llm="openai/gpt-4.1-mini",
        # tts="cartesia/sonic-3:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        tts=inference.TTS(
            model="inworld/inworld-tts-1",
            voice="Olivia",
        ),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
        mcp_servers=[pinecone],
    )

    await session.start(
        room=ctx.room,
        agent=Assistant(pinecone),
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind
                    == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )

    await session.generate_reply(
        instructions="Greet the user and offer your assistance."
    )


if __name__ == "__main__":
    agents.cli.run_app(server)
