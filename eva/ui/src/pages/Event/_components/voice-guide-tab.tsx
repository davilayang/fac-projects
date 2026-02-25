export function VoiceGuideTab() {
  return (
    <div className="event__voice-guide">
      <ul className="event__guide-steps">
        <li>
          Tap <strong>Talk To Agent</strong> directly on the player to start the
          voice session.
        </li>
        <li>
          Use voice commands like <em>pause the video</em>,{" "}
          <em>play the video</em>, or <em>jump to 1 minute 20 seconds</em>.
        </li>
        <li>
          You can also say <em>skip forward 30 seconds</em> or{" "}
          <em>rewind 15 seconds</em>.
        </li>
        <li>
          Say <em>bookmark this moment</em> to save a timestamp you can revisit
          later.
        </li>
        <li>
          Say <em>take a note</em> then dictate what to remember at this exact
          point.
        </li>
        <li>
          When the agent speaks, playback pauses automatically and then resumes.
        </li>
      </ul>

      <div className="event__api-callout">
        <p className="event__api-callout-title">Agent Control API</p>
        <p>
          Voice-agent integrations can call <code>window.eventVideoPlayer</code>{" "}
          for <code>play</code>, <code>pause</code>, <code>setCurrentTime</code>
          , and <code>seekBy</code>.
        </p>
        <p>
          You can also dispatch <code>event-video-player:command</code> with
          commands such as{" "}
          <code>{"{ action: 'setCurrentTime', time: 90 }"}</code>.
        </p>
      </div>
    </div>
  );
}
