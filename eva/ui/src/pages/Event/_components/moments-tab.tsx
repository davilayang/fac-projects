import { useEffect, useMemo, useState } from "react";
import {
  Bookmark,
  Clock3,
  FileText,
  Pencil,
  Plus,
  Trash2,
  X,
  Check,
} from "lucide-react";

interface EventVideoMoment {
  id: string;
  type: "bookmark" | "note";
  time: number;
  text: string;
  createdAt: string;
  source: "agent" | "user";
}

interface AddedMomentEventDetail {
  videoId: string;
  moment: EventVideoMoment;
}

const VIDEO_MOMENT_ADDED_EVENT = "event-video-moment:added";

function getMomentsStorageKey(videoId: string) {
  return `event-video-moments:${videoId}`;
}

function readMoments(videoId: string): EventVideoMoment[] {
  const raw = window.localStorage.getItem(getMomentsStorageKey(videoId));
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as EventVideoMoment[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeMoments(videoId: string, moments: EventVideoMoment[]) {
  window.localStorage.setItem(
    getMomentsStorageKey(videoId),
    JSON.stringify(moments)
  );
}

function formatSeconds(value: number) {
  const total = Math.max(0, Math.floor(value));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

/** Parse "m:ss" or "h:mm:ss" back to seconds. Returns NaN if invalid. */
function parseTimeInput(raw: string): number {
  const parts = raw
    .trim()
    .split(":")
    .map((p) => Number(p));
  if (parts.some((p) => !Number.isFinite(p) || p < 0)) return NaN;
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  return NaN;
}

function generateId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

// ── Shared edit form (used by both edit-in-place and add) ──────────────────

interface EditFormProps {
  type: "bookmark" | "note";
  initialText: string;
  initialTime: number;
  isAdd?: boolean;
  onSave: (text: string, time: number) => void;
  onCancel: () => void;
}

function EditForm({
  type,
  initialText,
  initialTime,
  isAdd,
  onSave,
  onCancel,
}: EditFormProps) {
  const [text, setText] = useState(initialText);
  const [timeStr, setTimeStr] = useState(formatSeconds(initialTime));
  const timeValid = Number.isFinite(parseTimeInput(timeStr));

  const handleSave = () => {
    const trimmed = text.trim();
    if (!trimmed || !Number.isFinite(parseTimeInput(timeStr))) return;
    onSave(trimmed, parseTimeInput(timeStr));
  };

  const modClass = type === "bookmark"
    ? "moment-edit-form--bookmark"
    : "moment-edit-form--note";

  return (
    <div className={`moment-edit-form ${modClass}${isAdd ? " moment-edit-form--add" : ""}`}>
      <textarea
        className="moment-edit-form__textarea"
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={type === "note" ? 3 : 2}
        placeholder={type === "bookmark" ? "Bookmark label…" : "Note text…"}
        autoFocus
      />
      <div className="moment-edit-form__row">
        <div className="moment-edit-form__time-wrap">
          <Clock3 className="moment-edit-form__time-icon" size={12} />
          <input
            className={`moment-edit-form__time-input${timeValid ? "" : " moment-edit-form__time-input--invalid"}`}
            value={timeStr}
            onChange={(e) => setTimeStr(e.target.value)}
            placeholder="m:ss"
            spellCheck={false}
          />
        </div>
        <div className="moment-edit-form__actions">
          <button
            type="button"
            className="moment-edit-form__btn moment-edit-form__btn--cancel"
            onClick={onCancel}
            aria-label="Cancel"
          >
            <X size={14} />
          </button>
          <button
            type="button"
            className="moment-edit-form__btn moment-edit-form__btn--save"
            onClick={handleSave}
            disabled={!text.trim() || !timeValid}
            aria-label={isAdd ? "Add" : "Save"}
          >
            <Check size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Bookmark item — compact waypoint chip ──────────────────────────────────

interface MomentItemProps {
  moment: EventVideoMoment;
  onDelete: (id: string) => void;
  onEdit: (id: string, text: string, time: number) => void;
}

function BookmarkItem({ moment, onDelete, onEdit }: MomentItemProps) {
  const [editing, setEditing] = useState(false);

  if (editing) {
    return (
      <EditForm
        type="bookmark"
        initialText={moment.text}
        initialTime={moment.time}
        onSave={(text, time) => {
          onEdit(moment.id, text, time);
          setEditing(false);
        }}
        onCancel={() => setEditing(false)}
      />
    );
  }

  return (
    <div className="moment-item moment-item--bookmark">
      <button
        type="button"
        className="moment-item__jump"
        onClick={() => window.eventVideoPlayer?.setCurrentTime(moment.time)}
        aria-label={`Jump to ${formatSeconds(moment.time)}`}
      >
        <Bookmark className="moment-item__bookmark-icon" size={13} aria-hidden />
        <span className="moment-item__bookmark-label">{moment.text}</span>
        <span className="moment-item__time-badge">
          <Clock3 size={10} aria-hidden />
          {formatSeconds(moment.time)}
        </span>
        {moment.source === "agent" && (
          <span className="moment-item__source-badge">AI</span>
        )}
      </button>
      <div className="moment-item__controls">
        <button
          type="button"
          className="moment-item__control-btn"
          onClick={() => setEditing(true)}
          aria-label="Edit"
        >
          <Pencil size={12} />
        </button>
        <button
          type="button"
          className="moment-item__control-btn moment-item__control-btn--danger"
          onClick={() => onDelete(moment.id)}
          aria-label="Delete"
        >
          <Trash2 size={12} />
        </button>
      </div>
    </div>
  );
}

// ── Note item — text-first card ────────────────────────────────────────────

function NoteItem({ moment, onDelete, onEdit }: MomentItemProps) {
  const [editing, setEditing] = useState(false);

  if (editing) {
    return (
      <EditForm
        type="note"
        initialText={moment.text}
        initialTime={moment.time}
        onSave={(text, time) => {
          onEdit(moment.id, text, time);
          setEditing(false);
        }}
        onCancel={() => setEditing(false)}
      />
    );
  }

  return (
    <div className="moment-item moment-item--note">
      <button
        type="button"
        className="moment-item__jump"
        onClick={() => window.eventVideoPlayer?.setCurrentTime(moment.time)}
        aria-label={`Jump to ${formatSeconds(moment.time)}`}
      >
        <p className="moment-item__note-text">{moment.text}</p>
        <span className="moment-item__note-meta">
          {moment.source === "agent" && (
            <span className="moment-item__source-badge">AI</span>
          )}
          <FileText size={10} aria-hidden />
          <Clock3 size={10} aria-hidden />
          {formatSeconds(moment.time)}
        </span>
      </button>
      <div className="moment-item__controls">
        <button
          type="button"
          className="moment-item__control-btn"
          onClick={() => setEditing(true)}
          aria-label="Edit"
        >
          <Pencil size={12} />
        </button>
        <button
          type="button"
          className="moment-item__control-btn moment-item__control-btn--danger"
          onClick={() => onDelete(moment.id)}
          aria-label="Delete"
        >
          <Trash2 size={12} />
        </button>
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

interface MomentsTabProps {
  videoId: string;
}

export function MomentsTab({ videoId }: MomentsTabProps) {
  const [moments, setMoments] = useState<EventVideoMoment[]>([]);
  const [addingType, setAddingType] = useState<"bookmark" | "note" | null>(null);

  useEffect(() => {
    setMoments(readMoments(videoId));
  }, [videoId]);

  useEffect(() => {
    const onMomentAdded = (event: Event) => {
      const customEvent = event as CustomEvent<AddedMomentEventDetail>;
      if (customEvent.detail?.videoId !== videoId) return;
      setMoments((prev) => [customEvent.detail.moment, ...prev]);
    };
    window.addEventListener(VIDEO_MOMENT_ADDED_EVENT, onMomentAdded as EventListener);
    return () => {
      window.removeEventListener(VIDEO_MOMENT_ADDED_EVENT, onMomentAdded as EventListener);
    };
  }, [videoId]);

  const bookmarks = useMemo(() => moments.filter((m) => m.type === "bookmark"), [moments]);
  const notes = useMemo(() => moments.filter((m) => m.type === "note"), [moments]);

  const deleteMoment = (id: string) => {
    setMoments((prev) => {
      const next = prev.filter((m) => m.id !== id);
      writeMoments(videoId, next);
      return next;
    });
  };

  const editMoment = (id: string, text: string, time: number) => {
    setMoments((prev) => {
      const next = prev.map((m) => (m.id === id ? { ...m, text, time } : m));
      writeMoments(videoId, next);
      return next;
    });
  };

  const addMoment = (type: "bookmark" | "note", text: string, time: number) => {
    const moment: EventVideoMoment = {
      id: generateId(),
      type,
      time,
      text,
      createdAt: new Date().toISOString(),
      source: "user",
    };
    setMoments((prev) => {
      const next = [moment, ...prev];
      writeMoments(videoId, next);
      return next;
    });
    setAddingType(null);
  };

  const currentTime = window.eventVideoPlayer?.getState().currentTime ?? 0;

  return (
    <div className="event__moments">
      <div className="event__moments-hint">
        <p>Say <em>bookmark this moment</em> to save a timestamp.</p>
        <p>Say <em>take a note</em> then dictate what to remember.</p>
        <p>Tap any saved moment to jump back instantly.</p>
      </div>

      {/* ── Bookmarks ── */}
      <section className="event__moments-section">
        <div className="event__moments-section-header">
          <h3 className="event__moments-section-title event__moments-section-title--bookmark">
            <Bookmark size={12} aria-hidden />
            Bookmarks
          </h3>
          <button
            type="button"
            className="event__moments-add-btn event__moments-add-btn--bookmark"
            onClick={() => setAddingType((t) => (t === "bookmark" ? null : "bookmark"))}
            aria-label="Add bookmark"
          >
            <Plus size={12} />
            Add
          </button>
        </div>

        {addingType === "bookmark" && (
          <EditForm
            type="bookmark"
            initialText="Bookmark"
            initialTime={currentTime}
            isAdd
            onSave={(text, time) => addMoment("bookmark", text, time)}
            onCancel={() => setAddingType(null)}
          />
        )}

        <div className="event__moments-list">
          {bookmarks.length === 0 ? (
            <p className="event__moments-empty">No bookmarks yet.</p>
          ) : (
            bookmarks.map((m) => (
              <BookmarkItem
                key={m.id}
                moment={m}
                onDelete={deleteMoment}
                onEdit={editMoment}
              />
            ))
          )}
        </div>
      </section>

      {/* ── Notes ── */}
      <section className="event__moments-section">
        <div className="event__moments-section-header">
          <h3 className="event__moments-section-title event__moments-section-title--note">
            <FileText size={12} aria-hidden />
            Notes
          </h3>
          <button
            type="button"
            className="event__moments-add-btn event__moments-add-btn--note"
            onClick={() => setAddingType((t) => (t === "note" ? null : "note"))}
            aria-label="Add note"
          >
            <Plus size={12} />
            Add
          </button>
        </div>

        {addingType === "note" && (
          <EditForm
            type="note"
            initialText=""
            initialTime={currentTime}
            isAdd
            onSave={(text, time) => addMoment("note", text, time)}
            onCancel={() => setAddingType(null)}
          />
        )}

        <div className="event__moments-list">
          {notes.length === 0 ? (
            <p className="event__moments-empty">No notes yet.</p>
          ) : (
            notes.map((m) => (
              <NoteItem
                key={m.id}
                moment={m}
                onDelete={deleteMoment}
                onEdit={editMoment}
              />
            ))
          )}
        </div>
      </section>
    </div>
  );
}
