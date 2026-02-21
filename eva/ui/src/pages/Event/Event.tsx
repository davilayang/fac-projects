import { useParams } from "react-router";

export function Event() {
  const { id } = useParams<{ id: string }>();

  return (
    <section>
      <header>
        <p>Now Playing</p>
        <h1>{id}</h1>
      </header>
    </section>
  );
}
