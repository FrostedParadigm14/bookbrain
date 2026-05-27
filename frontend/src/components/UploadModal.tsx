'use client';
import { useState } from 'react';

interface UploadModalProps {
  onClose: () => void;
  onUploadSuccess: (book: any) => void;
}

export default function UploadModal({ onClose, onUploadSuccess }: UploadModalProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [statusText, setStatusText] = useState('');

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
        throw new Error('Failed to upload file');
      }

      setStatusText('Indexing document chunks into Milvus Lite database...');
      const data = await response.json();

      setIsUploading(false);
      onUploadSuccess(data);
      onClose();
    } catch (error) {
      console.error(error);
      setStatusText('Error uploading and indexing document. Please try again.');
      setTimeout(() => {
        setIsUploading(false);
      }, 3000);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>&times;</button>
        
        <h2 style={{ marginBottom: '0.5rem' }}>Add to your Knowledge Base</h2>
        <p style={{ color: 'var(--leather-light)' }}>Upload a scholarly PDF or EPUB to extract metadata and enable query access.</p>

        {isUploading ? (
          <div className="upload-dropzone" style={{ cursor: 'wait' }}>
            <div className="upload-icon">⏳</div>
            <h3>{statusText}</h3>
          </div>
        ) : (
          <label className="upload-dropzone" style={{ display: 'block' }}>
            <input 
              type="file" 
              accept=".pdf,.epub" 
              style={{ display: 'none' }} 
              onChange={handleFileUpload}
            />
            <div className="upload-icon">📄</div>
            <h3>Click or Drag & Drop</h3>
            <p>Supports .PDF and .EPUB formats</p>
          </label>
        )}
      </div>
    </div>
  );
}

