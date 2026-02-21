import { useEffect, useRef, useState } from "react";
import { useLoaderData, useSearchParams, Link } from "react-router";
import { ROUTES, toEventDetail, type EventGalleryLoaderData } from "../../router";
import "./EventGallery.css";

const DEBOUNCE_MS = 400;

export function EventGallery() {
  const { data: videos, pagination } = useLoaderData<EventGalleryLoaderData>();
  const [searchParams, setSearchParams] = useSearchParams();
  const currentPage = pagination.currentPage;
  const hasPrev = currentPage > 1;
  const hasNext = currentPage < pagination.pagesTotal;

  // Seed input from URL so a hard refresh restores the search term
  const [inputValue, setInputValue] = useState(() => searchParams.get("q") ?? "");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Keep input in sync if the URL changes externally (e.g. back button)
  useEffect(() => {
    setInputValue(searchParams.get("q") ?? "");
  }, [searchParams]);

  function handleSearchChange(e: React.ChangeEvent<HTMLInputElement>) {
    const value = e.target.value;
    setInputValue(value);

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (value.trim()) {
          next.set("q", value.trim());
        } else {
          next.delete("q");
        }
        next.delete("page"); // reset to page 1 on new search
        return next;
      }, { replace: true });
    }, DEBOUNCE_MS);
  }

  function pageUrl(page: number) {
    const params = new URLSearchParams(searchParams);
    params.set("page", String(page));
    return `${ROUTES.EVENTS}?${params.toString()}`;
  }

  return (
    <section className="gallery">
      <header className="gallery__header">
        <div className="gallery__header-top">
          <div>
            <p className="gallery__eyebrow">Library</p>
            <h1 className="gallery__title">Events</h1>
          </div>
          <div className="gallery__search-wrap">
            <svg className="gallery__search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              className="gallery__search"
              type="search"
              placeholder="Search events…"
              value={inputValue}
              onChange={handleSearchChange}
              aria-label="Search events"
            />
          </div>
        </div>
      </header>

      {videos.length === 0 ? (
        <p className="gallery__empty">
          {inputValue.trim() ? `No events found for "${inputValue.trim()}".` : "No events found."}
        </p>
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
