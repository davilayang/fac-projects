import ApiVideoPlayer from "@api.video/react-player";

interface EventVideoPlayerProps {
  id: string;
}

export function EventVideoPlayer({ id }: EventVideoPlayerProps) {
  return (
    <section id="video-player-section">
      <ApiVideoPlayer
        video={{ id }}
        style={{ height: "480px" }}
        responsive={true}
      />
    </section>
  );
}
