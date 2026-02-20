import json

from dotenv import load_dotenv
from livekit import agents, rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    RunContext,
    StopResponse,
    ToolError,
    function_tool,
    inference,
    room_io,
)
from livekit.plugins import noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

load_dotenv(".env.local")


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful voice AI assistant for an interactive video page.
            You eagerly assist users with their questions by providing information from your extensive knowledge.
            Your responses are concise, to the point, and without any complex formatting or punctuation including emojis, asterisks, or other symbols.
            You are curious, friendly, and have a sense of humor.
            You can fully control the video through tools.
            If the user asks to play, pause, jump to a timestamp, rewind, or skip forward/backward,
            always use the corresponding video control tool instead of explaining what to click.
            If the user asks to remember something, save a bookmark, or write a note,
            use add_video_bookmark or add_video_note.
            set_video_timestamp uses an absolute timestamp in seconds from the start.
            seek_video_by uses a relative offset in seconds where positive is forward and negative is backward.
            For jump and seek operations, do not speak after the tool succeeds. Let the user watch.""",
        )

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
    async def play_video(self, context: RunContext) -> str:
        """Resume or start playing the video."""
        await self._rpc(context, "video.play")
        return "Video is now playing."

    @function_tool()
    async def pause_video(self, context: RunContext) -> str:
        """Pause the video."""
        await self._rpc(context, "video.pause")
        return "Video paused."

    @function_tool()
    async def set_video_timestamp(self, context: RunContext, seconds: float) -> str:
        """Jump the user's video to an absolute timestamp in seconds from the start."""
        if seconds < 0:
            raise ToolError("Timestamp must be 0 seconds or greater.")
        await self._rpc(context, "video.setCurrentTime", {"time": seconds})
        return f"Jumped to {seconds:.1f} seconds."

    @function_tool()
    async def seek_video_by(self, context: RunContext, delta: float) -> str:
        """Seek the video forward or backward by a relative number of seconds. Positive values seek forward, negative values seek backward."""
        await self._rpc(context, "video.seekBy", {"delta": delta})
        direction = "forward" if delta >= 0 else "backward"
        return f"Seeked {direction} by {abs(delta):.1f} seconds."

    @function_tool()
    async def add_video_bookmark(
        self, context: RunContext, label: str = "Bookmark", time: float | None = None
    ) -> str:
        """Save a bookmark at the current video position or at a specific time. Use when the user asks to remember a moment or save a bookmark."""
        payload: dict = {"label": label}
        if time is not None:
            payload["time"] = time
        await self._rpc(context, "video.addBookmark", payload)
        return f"Bookmark '{label}' saved."

    @function_tool()
    async def add_video_note(
        self, context: RunContext, text: str, time: float | None = None
    ) -> str:
        """Save a text note at the current video position or at a specific time. Use when the user asks to write down or note something."""
        payload: dict = {"text": text}
        if time is not None:
            payload["time"] = time
        await self._rpc(context, "video.addNote", payload)
        return f"Note saved."


server = AgentServer()


@server.rtc_session(agent_name="eva")
async def my_agent(ctx: agents.JobContext):

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
    )

    await session.start(
        room=ctx.room,
        agent=Assistant(),
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
