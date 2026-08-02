'use client';
import { useState } from 'react';

interface UploadModalProps {
  onClose: () => void;
  onUploadSuccess: (book: any) => void;
}

export default function UploadModal({ onClose, onUploadSuccess }: UploadModalProps) {
  const [activeTab, setActiveTab] = useState<'local' | 'gdrive'>('local');
  const [isUploading, setIsUploading] = useState(false);
  const [statusText, setStatusText] = useState('');
  const [gdriveUrl, setGdriveUrl] = useState('');

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setStatusText('Uploading file to server...');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/v1/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to upload file');
      }

      setStatusText('Indexing document chunks into Milvus Lite database...');
      const data = await response.json();

      setIsUploading(false);
      onUploadSuccess(data);
      onClose();
    } catch (error: any) {
      console.error(error);
      setStatusText(`Error: ${error.message || 'Failed to upload'}. Please try again.`);
      setTimeout(() => {
        setIsUploading(false);
      }, 3500);
    }
  };

  const handleGDriveImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!gdriveUrl.trim()) return;

    setIsUploading(true);
    setStatusText('Downloading EPUB from Google Drive (public or restricted)...');

    try {
      const response = await fetch('http://127.0.0.1:8000/api/v1/gdrive/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gdriveUrl: gdriveUrl.trim() }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Google Drive import failed');
      }

      setStatusText('Ingesting metadata and vectors into library...');
      const bookData = await response.json();

      setIsUploading(false);
      onUploadSuccess(bookData);
      onClose();
    } catch (error: any) {
      console.error(error);
      setStatusText(`Error: ${error.message || 'GDrive import failed'}. Please check your link.`);
      setTimeout(() => {
        setIsUploading(false);
      }, 4000);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '520px' }}>
        <button className="modal-close" onClick={onClose}>&times;</button>
        
        <h2 style={{ marginBottom: '0.5rem' }}>Add Book to Library</h2>
        <p style={{ color: 'var(--leather-light)', marginBottom: '1.25rem', fontSize: '0.9rem' }}>
          Import an EPUB or PDF from local disk or directly via a Google Drive link.
        </p>

        {/* Tab Selector */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
          <button
            type="button"
            onClick={() => setActiveTab('local')}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: '6px',
              border: 'none',
              background: activeTab === 'local' ? 'var(--accent-color)' : 'transparent',
              color: activeTab === 'local' ? '#fff' : 'var(--text-color)',
              fontWeight: 600,
              cursor: 'pointer',
              fontSize: '0.875rem'
            }}
          >
            💻 Local File Upload
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('gdrive')}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: '6px',
              border: 'none',
              background: activeTab === 'gdrive' ? 'var(--accent-color)' : 'transparent',
              color: activeTab === 'gdrive' ? '#fff' : 'var(--text-color)',
              fontWeight: 600,
              cursor: 'pointer',
              fontSize: '0.875rem'
            }}
          >
            ☁️ Google Drive Link
          </button>
        </div>

        {isUploading ? (
          <div className="upload-dropzone" style={{ cursor: 'wait', padding: '2.5rem 1.5rem' }}>
            <div className="upload-icon">⏳</div>
            <h3 style={{ fontSize: '1rem', marginTop: '0.5rem' }}>{statusText}</h3>
          </div>
        ) : activeTab === 'local' ? (
          <label className="upload-dropzone" style={{ display: 'block', cursor: 'pointer' }}>
            <input 
              type="file" 
              accept=".pdf,.epub" 
              style={{ display: 'none' }} 
              onChange={handleFileUpload}
            />
            <div className="upload-icon">📄</div>
            <h3>Click or Drag & Drop File</h3>
            <p>Supports .PDF and .EPUB formats</p>
          </label>
        ) : (
          <form onSubmit={handleGDriveImport} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem' }}>
                Google Drive Share URL
              </label>
              <input
                type="url"
                placeholder="https://drive.google.com/file/d/... or restricted link"
                value={gdriveUrl}
                onChange={(e) => setGdriveUrl(e.target.value)}
                required
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  borderRadius: '8px',
                  border: '1px solid var(--border-color)',
                  background: 'var(--bg-input, #1e1e1e)',
                  color: 'var(--text-color, #fff)',
                  fontSize: '0.9rem'
                }}
              />
            </div>
            <button
              type="submit"
              className="btn-primary"
              style={{
                width: '100%',
                padding: '0.75rem',
                borderRadius: '8px',
                fontWeight: 600,
                cursor: 'pointer',
                marginTop: '0.5rem'
              }}
            >
              📥 Import from Google Drive
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
