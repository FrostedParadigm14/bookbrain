'use client';
import { useState, useEffect } from 'react';
import ChatWidget from '../components/ChatWidget';
import UploadModal from '../components/UploadModal';
import BookDetailDrawer from '../components/BookDetailDrawer';

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

interface DiagnosticsData {
  collectionName: string;
  totalChunks: number;
  dbFileSize: number;
  vectorDimension: number;
  embeddingModel: string;
  activeLlmProvider: string;
  chunks: Array<{
    id: string;
    text: string;
    filePath: string;
    page: number;
    title: string;
    author: string;
  }>;
  uniqueBooks: Array<{
    filePath: string;
    title: string;
    author: string;
  }>;
}

export default function Home() {
  const [books, setBooks] = useState<Book[]>([]);
  const [selectedBooks, setSelectedBooks] = useState<string[]>([]);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isDiagnosticsOpen, setIsDiagnosticsOpen] = useState(false);
  const [isLoadingDiagnostics, setIsLoadingDiagnostics] = useState(false);
  const [diagnosticsData, setDiagnosticsData] = useState<DiagnosticsData | null>(null);
  const [isLoadingBooks, setIsLoadingBooks] = useState(true);
  const [bookToDelete, setBookToDelete] = useState<Book | null>(null);
  const [detailBook, setDetailBook] = useState<Book | null>(null);

  // Fetch books from real SQLite backend
  const fetchBooks = async () => {
    try {
      setIsLoadingBooks(true);
      const response = await fetch('http://127.0.0.1:8000/api/v1/books');
      if (response.ok) {
        const data = await response.json();
        setBooks(data);
      }
    } catch (error) {
      console.error('Error fetching library:', error);
    } finally {
      setIsLoadingBooks(false);
    }
  };

  useEffect(() => {
    fetchBooks();
  }, []);

  const handleToggleBook = (filePath: string) => {
    setSelectedBooks((prev) =>
      prev.includes(filePath)
        ? prev.filter((p) => p !== filePath)
        : [...prev, filePath]
    );
  };

  const handleSelectAll = () => {
    if (selectedBooks.length === books.length) {
      setSelectedBooks([]);
    } else {
      setSelectedBooks(books.map((b) => b.filePath));
    }
  };

  const handleDeleteBook = async (bookId: number, filePath: string) => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/v1/books/${bookId}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        setBooks((prev) => prev.filter((b) => b.id !== bookId));
        setSelectedBooks((prev) => prev.filter((p) => p !== filePath));
        setBookToDelete(null);
      } else {
        const err = await response.json();
        alert(`Failed to delete book: ${err.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error deleting book:', error);
      alert('Network error while deleting book.');
    }
  };

  const [diagFilterBook, setDiagFilterBook] = useState<string>('');

  // Fetch Milvus Lite statistics
  const fetchDiagnostics = async (filePath?: string) => {
    try {
      setIsLoadingDiagnostics(true);
      const url = filePath
        ? `http://127.0.0.1:8000/api/v1/diagnostics?file_path=${encodeURIComponent(filePath)}`
        : 'http://127.0.0.1:8000/api/v1/diagnostics';
      const response = await fetch(url);
      if (response.ok) {
        const data = await response.json();
        setDiagnosticsData(data);
      }
    } catch (error) {
      console.error('Error fetching diagnostics:', error);
    } finally {
      setIsLoadingDiagnostics(false);
    }
  };

  const handleOpenDiagnostics = () => {
    setIsDiagnosticsOpen(true);
    setDiagFilterBook('');
    fetchDiagnostics();
  };

  const handleOpenDiagnosticsForBook = (filePath: string) => {
    setIsDiagnosticsOpen(true);
    setDiagFilterBook(filePath);
    fetchDiagnostics(filePath);
    setDetailBook(null);
  };

  const handleDiagFilterChange = (filePath: string) => {
    setDiagFilterBook(filePath);
    fetchDiagnostics(filePath || undefined);
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <>
      <nav className="navbar">
        <a href="/" className="nav-brand">
          <span className="nav-brand-icon">✧</span>
          BookBrain
        </a>

        <div className="nav-controls">
          <button
            className="btn-secondary"
            onClick={handleOpenDiagnostics}
            style={{ marginRight: '0.5rem' }}
          >
            📊 DB Diagnostics
          </button>
          <button
            className="btn-primary"
            onClick={() => setIsUploadOpen(true)}
          >
            + Add Book
          </button>
        </div>
      </nav>

      <main className="container">
        <section className="header-section">
          <h1>AI-Powered Digital Library</h1>
          <p>
            Explore your collection, upload PDFs or EPUBs into **Milvus Lite**,
            and query specific books using the Librarian Agent.
          </p>
        </section>

        {books.length > 0 && (
          <div className="selection-toolbar">
            <button className="btn-text" onClick={handleSelectAll}>
              {selectedBooks.length === books.length ? 'Clear Selection' : 'Select All Books'}
            </button>
            <span style={{ color: 'var(--leather-light)', fontSize: '0.9rem' }}>
              ({selectedBooks.length} of {books.length} books selected as agent search context)
            </span>
          </div>
        )}

        {isLoadingBooks ? (
          <div style={{ textAlign: 'center', padding: '3rem' }}>
            <div className="upload-icon">⏳</div>
            <p>Loading your digital library...</p>
          </div>
        ) : books.length === 0 ? (
          <div className="empty-library-state">
            <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>📚</div>
            <h2>Your Library is Empty</h2>
            <p style={{ color: 'var(--leather-light)', marginBottom: '1.5rem' }}>
              Upload your first book (PDF or EPUB) to begin chunking, embedding, and indexing into Milvus Lite!
            </p>
            <button className="btn-primary" onClick={() => setIsUploadOpen(true)}>
              Upload First Book
            </button>
          </div>
        ) : (
          <section className="library-grid">
            {books.map((book) => {
              const isSelected = selectedBooks.includes(book.filePath);
              const stars = book.rating ? '★'.repeat(book.rating) + '☆'.repeat(5 - book.rating) : null;
              return (
                <div
                  key={book.id}
                  className={`book-card ${isSelected ? 'selected' : ''}`}
                  onClick={() => handleToggleBook(book.filePath)}
                >
                  <div className="book-cover-wrapper">
                    {book.coverUrl ? (
                      /* eslint-disable-next-line @next/next/no-img-element */
                      <img src={book.coverUrl} alt={book.title} className="book-cover" />
                    ) : (
                      <div className="book-placeholder">
                        {book.title}
                      </div>
                    )}
                    {/* Info / edit metadata button */}
                    <button
                      className="info-book-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDetailBook(book);
                      }}
                      title="Edit Metadata"
                    >
                      ✏️
                    </button>
                    {/* Delete button */}
                    <button
                      className="delete-book-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        setBookToDelete(book);
                      }}
                      title="Delete Book"
                    >
                      🗑️
                    </button>
                    {/* Reading status badge */}
                    {book.readingStatus && book.readingStatus !== 'unread' && (
                      <span className={`book-status-badge ${book.readingStatus}`}>
                        {book.readingStatus}
                      </span>
                    )}
                    <div className="book-selection-overlay">
                      <div className="selection-badge">{isSelected ? '✓ Active' : 'Select'}</div>
                    </div>
                  </div>
                  <div className="book-info">
                    <div className="book-title">{book.title}</div>
                    <div className="book-author">{book.author}</div>
                    {book.genre && <div style={{ fontSize: '0.75rem', color: 'var(--leather-light)', marginTop: '0.15rem' }}>{book.genre}</div>}
                    {stars && <div className="book-card-stars">{stars}</div>}
                  </div>
                </div>
              );
            })}
          </section>
        )}
      </main>

      {isUploadOpen && (
        <UploadModal
          onClose={() => setIsUploadOpen(false)}
          onUploadSuccess={(newBook) => {
            setBooks(prev => [...prev, newBook]);
            setSelectedBooks(prev => [...prev, newBook.filePath]);
          }}
        />
      )}

      {isDiagnosticsOpen && (
        <div className="modal-overlay" onClick={() => setIsDiagnosticsOpen(false)}>
          <div className="diagnostics-drawer" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-header">
              <h2>Milvus Lite DB Explorer</h2>
              <button className="modal-close" onClick={() => setIsDiagnosticsOpen(false)}>&times;</button>
            </div>
            
            {/* Book filter selector */}
            <div className="diag-filter-bar">
              <label className="diag-filter-label" htmlFor="diag-book-select">📚 Filter by Book</label>
              <select
                id="diag-book-select"
                className="diag-book-select"
                value={diagFilterBook}
                onChange={(e) => handleDiagFilterChange(e.target.value)}
              >
                <option value="">— All books ({diagnosticsData?.totalChunks ?? '…'} total chunks) —</option>
                {(diagnosticsData?.uniqueBooks ?? []).map(b => (
                  <option key={b.filePath} value={b.filePath}>
                    {b.title} by {b.author}
                  </option>
                ))}
              </select>
            </div>

            {isLoadingDiagnostics ? (
              <div style={{ textAlign: 'center', padding: '3rem' }}>
                <div className="upload-icon">⏳</div>
                <p>Loading diagnostics statistics...</p>
              </div>
            ) : diagnosticsData ? (
              <div className="drawer-body">
                <div className="diagnostics-stats-grid">
                  <div className="stat-card">
                    <span className="stat-label">Collection</span>
                    <span className="stat-val">{diagnosticsData.collectionName}</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">Total Chunks</span>
                    <span className="stat-val">{diagnosticsData.totalChunks}</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">DB File Size</span>
                    <span className="stat-val">{formatBytes(diagnosticsData.dbFileSize)}</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">Vectors</span>
                    <span className="stat-val">{diagnosticsData.vectorDimension}d</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">LLM Provider</span>
                    <span className="stat-val" style={{ textTransform: 'capitalize' }}>
                      {diagnosticsData.activeLlmProvider}
                    </span>
                  </div>
                </div>

                <h3 style={{ margin: '1.5rem 0 1rem 0', fontFamily: 'Merriweather, serif' }}>
                  {diagFilterBook
                    ? <>Chunks for <em>{diagnosticsData.uniqueBooks.find(b => b.filePath === diagFilterBook)?.title ?? books.find(b => b.filePath === diagFilterBook)?.title ?? 'selected book'}</em> ({diagnosticsData.chunks.length})</>
                    : <>All Indexed Chunks ({diagnosticsData.chunks.length})</>}
                </h3>
                <div className="chunks-list">
                  {diagnosticsData.chunks.length === 0 ? (
                    <p style={{ color: 'var(--leather-light)', fontStyle: 'italic', padding: '1rem 0' }}>
                      {diagFilterBook
                        ? 'No chunks found for this book. It may not have been ingested yet.'
                        : 'No vector chunks stored yet. Upload a book to populate the Milvus database.'}
                    </p>
                  ) : (
                    diagnosticsData.chunks.map((chunk) => (
                      <div key={chunk.id} className="chunk-card">
                        <p className="chunk-text">&ldquo;{chunk.text}&rdquo;</p>
                        <div className="chunk-meta">
                          <span>📖 {chunk.title} ({chunk.author})</span>
                          <span>Page {chunk.page}</span>
                          <span className="chunk-id-tag">ID: {chunk.id.substring(0, 16)}...</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            ) : (
              <p style={{ padding: '2rem', color: 'red' }}>Failed to retrieve diagnostics from backend.</p>
            )}
          </div>
        </div>
      )}

      {bookToDelete && (
        <div className="modal-overlay" onClick={() => setBookToDelete(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setBookToDelete(null)}>&times;</button>
            <h2 style={{ marginBottom: '1rem', color: 'var(--accent-red)' }}>Confirm Deletion</h2>
            <p>
              Are you sure you want to remove <strong>{bookToDelete.title}</strong> by <strong>{bookToDelete.author}</strong>?
            </p>
            <p style={{ marginTop: '0.5rem', fontSize: '0.9rem', color: 'var(--leather-light)' }}>
              This will permanently delete the physical file, purge all its vector chunks from the Milvus database, and remove its metadata.
            </p>
            <div className="confirmation-card-actions">
              <button className="btn-secondary" onClick={() => setBookToDelete(null)}>
                Cancel
              </button>
              <button 
                className="btn-danger" 
                onClick={() => handleDeleteBook(bookToDelete.id, bookToDelete.filePath)}
              >
                Delete Permanently
              </button>
            </div>
          </div>
        </div>
      )}

      {detailBook && (
        <BookDetailDrawer
          book={detailBook}
          onClose={() => setDetailBook(null)}
          onSave={(updated) => {
            setBooks(prev => prev.map(b => b.id === updated.id ? { ...b, ...updated } : b));
          }}
          onViewDiagnostics={(filePath) => handleOpenDiagnosticsForBook(filePath)}
        />
      )}

      <ChatWidget selectedBooks={selectedBooks} />
    </>
  );
}

