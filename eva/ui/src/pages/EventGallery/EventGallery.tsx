import { useLoaderData, useSearchParams, Link } from "react-router";
import { ROUTES, toEventDetail, type EventGalleryLoaderData } from "../../router";
import "./EventGallery.css";

export function EventGallery() {
  const { data: videos, pagination } = useLoaderData<EventGalleryLoaderData>();
  const [searchParams] = useSearchParams();
  const currentPage = pagination.currentPage;
  const hasPrev = currentPage > 1;
  const hasNext = currentPage < pagination.pagesTotal;

  function pageUrl(page: number) {
    const params = new URLSearchParams(searchParams);
    params.set("page", String(page));
    return `${ROUTES.EVENTS}?${params.toString()}`;
  }

  return (
    <section className="gallery">
      <header className="gallery__header">
        <p className="gallery__eyebrow">Library</p>
        <h1 className="gallery__title">Events</h1>
      </header>

      {videos.length === 0 ? (
        <p className="gallery__empty">No events found.</p>
      ) : (
        <ul className="gallery__grid">
          {videos.map((video) => (
            <li key={video.videoId} className="gallery__item">
              <Link to={toEventDetail(video.videoId)} className="gallery__card">
                {video.assets?.thumbnail ? (
                  <img
                    className="gallery__thumb"
                    src={video.assets.thumbnail}
                    alt={video.title ?? "Event thumbnail"}
                    loading="lazy"
                  />
                ) : (
                  <div className="gallery__thumb gallery__thumb--placeholder" aria-hidden="true" />
                )}
                <div className="gallery__info">
                  <p className="gallery__name">{video.title ?? "Untitled event"}</p>
                  {video.publishedAt && (
                    <p className="gallery__date">
                      {new Date(video.publishedAt).toLocaleDateString("en-GB", {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </p>
                  )}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}

      {pagination.pagesTotal > 1 && (
        <nav className="gallery__pagination" aria-label="Pagination">
          {hasPrev ? (
            <Link to={pageUrl(currentPage - 1)} className="gallery__page-btn">
              ← Previous
            </Link>
          ) : (
            <span className="gallery__page-btn gallery__page-btn--disabled">← Previous</span>
          )}

          <span className="gallery__page-info">
            Page {currentPage} of {pagination.pagesTotal}
          </span>

          {hasNext ? (
            <Link to={pageUrl(currentPage + 1)} className="gallery__page-btn">
              Next →
            </Link>
          ) : (
            <span className="gallery__page-btn gallery__page-btn--disabled">Next →</span>
          )}
        </nav>
      )}
    </section>
  );
}
