import asyncio
import json
import os

import httpx
from textwrap import dedent
from dotenv import load_dotenv
from pinecone import Pinecone
from livekit import agents, rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    RunContext,
    ToolError,
    function_tool,
    inference,
    room_io,
)
from livekit.plugins import noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

load_dotenv(".env")
load_dotenv(".env.local", override=True)


PINECONE_NAMESPACE = "evt_spreadsheet_hacks"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-large"


class Assistant(Agent):
    def __init__(self, index) -> None:
        super().__init__(
            instructions=dedent("""\
                You are a helpful voice AI assistant for an interactive video page.
                You eagerly assist users with their questions by providing
                information from your extensive knowledge.
                Your responses are concise, to the point, and without any complex
                formatting or punctuation including emojis, asterisks, or other symbols.

                You are curious, friendly, and have a sense of humor.
                You can fully control the video through tools.

                If the user asks to play, pause, jump to a timestamp, rewind,
                or skip forward/backward, always use the corresponding video
                control tool instead of explaining what to click.

                If the user asks to remember something, save a bookmark, or write a note, use add_video_bookmark or add_video_note.
            """),
        )
        self._index = index

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
    async def search_video_content(
        self,
        context: RunContext,
        query_text: str,
        speaker_name: str | None = None,
        start_after_seconds: float | None = None,
        end_before_seconds: float | None = None,
        section: str | None = None,
    ) -> str:
        """Search the video transcript for relevant segments by topic or keyword,
        with optional filters on speaker, time range, or section.
        Use when the user asks what was said, discussed, or covered in the video.
        Do not use for video playback control.

        Args:
            query_text: A natural-language description of the topic or content to find.
            speaker_name: Filter results to a specific speaker. Use when the user asks
                what a particular person said.
            start_after_seconds: Only return segments starting after this timestamp in
                seconds. Use for queries like "in the last 10 minutes" or "after the break".
            end_before_seconds: Only return segments ending before this timestamp in
                seconds. Use for queries like "in the first 5 minutes".
            section: Filter results to a specific section of the video.
        """
        # Step 1: embed the query text with OpenAI
        async with httpx.AsyncClient() as client:
            emb_response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
                    "Content-Type": "application/json",
                },
                json={"model": OPENAI_EMBEDDING_MODEL, "input": query_text},
                timeout=15,
            )
        if emb_response.status_code != 200:
            raise ToolError(f"Embedding failed ({emb_response.status_code}): {emb_response.text}")
        vector = emb_response.json()["data"][0]["embedding"]

        # Build metadata filter from optional parameters
        conditions = []
        if speaker_name is not None:
            conditions.append({"speaker_name": {"$eq": speaker_name}})
        if start_after_seconds is not None:
            conditions.append({"start_seconds": {"$gte": start_after_seconds}})
        if end_before_seconds is not None:
            conditions.append({"end_seconds": {"$lte": end_before_seconds}})
        if section is not None:
            conditions.append({"section": {"$eq": section}})
        metadata_filter = {"$and": conditions} if len(conditions) > 1 else conditions[0] if conditions else None

        # Step 2: query Pinecone with the vector using the Python SDK
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._index.query(
                vector=vector,
                top_k=10,
                namespace=PINECONE_NAMESPACE,
                include_metadata=True,
                filter=metadata_filter,
            ),
        )
        matches = response.get("matches", [])
        if not matches:
            return "No relevant segments found."
        return json.dumps([
            {"id": m["id"], "score": m["score"], "metadata": m.get("metadata", {})}
            for m in matches
        ])

    @function_tool()
    async def play_video(self, context: RunContext) -> str:
        """Resume or start playing the video.
        Use when the user asks to play, resume, or start the video."""
        await self._rpc(context, "video.play")
        return "Video is now playing."

    @function_tool()
    async def pause_video(self, context: RunContext) -> str:
        """Pause the video.
        Use when the user asks to pause or stop the video."""
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
    pc = Pinecone(api_key=os.environ["PINECONE_API_TOKEN"])
    index = pc.Index(host=os.environ["PINECONE_INDEX_HOST"])

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
        agent=Assistant(index),
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
