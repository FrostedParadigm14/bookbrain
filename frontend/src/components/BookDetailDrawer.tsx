'use client';
import { useState, useEffect } from 'react';

interface Book {
  id: number;
  title: string;
  author: string;
  coverUrl: string;
  filePath: string;
  genre?: string;
  readingStatus?: string;
  rating?: number;
  notes?: string;
  lastReadAt?: string;
  pageCount?: number;
  description?: string;
  addedAt?: string;
}

interface BookDetailDrawerProps {
  book: Book;
  onClose: () => void;
  onSave: (updated: Book) => void;
  onViewDiagnostics?: (filePath: string) => void;
}

const GENRES = [
  'Fiction', 'Non-Fiction', 'Science Fiction', 'Fantasy', 'Mystery',
  'Thriller', 'Romance', 'Historical Fiction', 'Biography', 'Memoir',
  'Self-Help', 'Philosophy', 'Science', 'Technology', 'Business',
  'Psychology', 'History', 'Poetry', 'Horror', 'Graphic Novel',
];

const STATUS_OPTIONS = [
  { value: 'unread', label: '📚 Unread', color: 'var(--leather-light)' },
  { value: 'reading', label: '📖 Reading', color: '#2563eb' },
  { value: 'completed', label: '✅ Completed', color: '#16a34a' },
  { value: 'abandoned', label: '🚫 Abandoned', color: 'var(--accent-red)' },
];

export default function BookDetailDrawer({ book, onClose, onSave, onViewDiagnostics }: BookDetailDrawerProps) {
  const [genre, setGenre] = useState(book.genre || '');
  const [readingStatus, setReadingStatus] = useState(book.readingStatus || 'unread');
  const [rating, setRating] = useState(book.rating || 0);
  const [hoverRating, setHoverRating] = useState(0);
  const [notes, setNotes] = useState(book.notes || '');
  const [description, setDescription] = useState(book.description || '');
  const [lastReadAt, setLastReadAt] = useState(book.lastReadAt ? book.lastReadAt.split('T')[0] : '');
  const [isSaving, setIsSaving] = useState(false);

  // Reset on book change
  useEffect(() => {
    setGenre(book.genre || '');
    setReadingStatus(book.readingStatus || 'unread');
    setRating(book.rating || 0);
    setNotes(book.notes || '');
    setDescription(book.description || '');
    setLastReadAt(book.lastReadAt ? book.lastReadAt.split('T')[0] : '');
  }, [book.id]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const payload: Record<string, string | number | null> = {};
      if (genre) payload.genre = genre;
      if (readingStatus) payload.readingStatus = readingStatus;
      if (rating > 0) payload.rating = rating;
      if (notes.trim()) payload.notes = notes.trim();
      if (description.trim()) payload.description = description.trim();
      if (lastReadAt) payload.lastReadAt = lastReadAt;

      const response = await fetch(`http://127.0.0.1:8000/api/v1/books/${book.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const updated = await response.json();
        onSave(updated);
        onClose();
      } else {
        const err = await response.json();
        alert(`Failed to save: ${err.detail || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Save error:', err);
      alert('Network error while saving metadata.');
    } finally {
      setIsSaving(false);
    }
  };

  const statusOption = STATUS_OPTIONS.find(s => s.value === readingStatus);

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'Never';
    try {
      return new Date(dateStr).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    } catch { return dateStr; }
  };

  return (
    <>
      {/* Backdrop */}
      <div className="modal-overlay" onClick={onClose} />

      {/* Drawer */}
      <div className="book-detail-drawer">
        {/* Header */}
        <div className="detail-drawer-header">
          <div>
            <h2 className="detail-drawer-title">{book.title}</h2>
            <p className="detail-drawer-author">by {book.author}</p>
          </div>
          <button className="modal-close" onClick={onClose} style={{ color: 'var(--parchment)', position: 'static', fontSize: '1.5rem' }}>
            &times;
          </button>
        </div>

        {/* Body */}
        <div className="detail-drawer-body">

          {/* Reading Status */}
          <div className="detail-section">
            <label className="detail-label">Reading Status</label>
            <div className="status-pills">
              {STATUS_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  className={`status-pill ${readingStatus === opt.value ? 'active' : ''}`}
                  style={readingStatus === opt.value ? { borderColor: opt.color, color: opt.color, background: `${opt.color}15` } : {}}
                  onClick={() => setReadingStatus(opt.value)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Star Rating */}
          <div className="detail-section">
            <label className="detail-label">Your Rating</label>
            <div className="star-rating">
              {[1, 2, 3, 4, 5].map(star => (
                <button
                  key={star}
                  className="star-btn"
                  onMouseEnter={() => setHoverRating(star)}
                  onMouseLeave={() => setHoverRating(0)}
                  onClick={() => setRating(rating === star ? 0 : star)}
                >
                  <span className={star <= (hoverRating || rating) ? 'star filled' : 'star'}>★</span>
                </button>
              ))}
              {rating > 0 && (
                <span className="rating-label">{rating}/5</span>
              )}
            </div>
          </div>

          {/* Genre */}
          <div className="detail-section">
            <label className="detail-label" htmlFor="genre-select">Genre</label>
            <div className="detail-input-row">
              <select
                id="genre-select"
                className="detail-select"
                value={genre}
                onChange={e => setGenre(e.target.value)}
              >
                <option value="">— Select genre —</option>
                {GENRES.map(g => (
                  <option key={g} value={g}>{g}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Last Read */}
          <div className="detail-section">
            <label className="detail-label" htmlFor="last-read-input">Last Read</label>
            <input
              id="last-read-input"
              type="date"
              className="detail-input"
              value={lastReadAt}
              onChange={e => setLastReadAt(e.target.value)}
            />
            {book.lastReadAt && (
              <p className="detail-hint">Previously saved: {formatDate(book.lastReadAt)}</p>
            )}
          </div>

          {/* Description */}
          <div className="detail-section">
            <label className="detail-label" htmlFor="description-input">Book Description</label>
            <textarea
              id="description-input"
              className="detail-textarea"
              placeholder="Book summary / description (automatically populated by Bookkeeper Agent)..."
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={4}
            />
          </div>

          {/* Notes */}
          <div className="detail-section">
            <label className="detail-label" htmlFor="notes-input">Notes & Thoughts</label>
            <textarea
              id="notes-input"
              className="detail-textarea"
              placeholder="Your thoughts, quotes, takeaways..."
              value={notes}
              onChange={e => setNotes(e.target.value)}
              rows={5}
            />
          </div>

          {/* Diagnostics inspector button */}
          {onViewDiagnostics && (
            <div className="detail-section" style={{ marginTop: '1.5rem' }}>
              <button
                className="btn-secondary"
                onClick={() => onViewDiagnostics(book.filePath)}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem',
                  padding: '0.75rem',
                  fontSize: '0.9rem',
                  borderRadius: '0.5rem',
                  border: '1px solid var(--gold)',
                  color: 'var(--leather)',
                  fontWeight: '600',
                  background: 'rgba(212, 175, 55, 0.08)',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease'
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.background = 'rgba(212, 175, 55, 0.15)';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.background = 'rgba(212, 175, 55, 0.08)';
                }}
              >
                📊 Inspect DB Vector Chunks
              </button>
            </div>
          )}

          {/* Read-only metadata */}
          {book.addedAt && (
            <div className="detail-section detail-meta-row">
              <span className="detail-meta-label">Added to library</span>
              <span className="detail-meta-value">{formatDate(book.addedAt)}</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="detail-drawer-footer">
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={handleSave} disabled={isSaving}>
            {isSaving ? 'Saving...' : '💾 Save Metadata'}
          </button>
        </div>
      </div>
    </>
  );
}
