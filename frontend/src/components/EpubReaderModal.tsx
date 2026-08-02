'use client';
import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';

// Dynamically import ReactReader to avoid SSR window issues
const ReactReaderComponent = dynamic(
  async () => {
    const { ReactReader, ReactReaderStyle } = await import('react-reader');
    return function ReaderComponent({
      url,
      location,
      locationChanged,
      tocChanged,
      themeStyles,
    }: {
      url: string | ArrayBuffer;
      location: string | number;
      locationChanged: (loc: string | number) => void;
      tocChanged?: (toc: any[]) => void;
      themeStyles: { bg: string; color: string };
    }) {
      const customStyles = {
        ...ReactReaderStyle,
        container: {
          ...ReactReaderStyle.container,
          backgroundColor: themeStyles.bg,
        },
        readerArea: {
          ...ReactReaderStyle.readerArea,
          backgroundColor: themeStyles.bg,
        },
        tocArea: {
          ...ReactReaderStyle.tocArea,
          backgroundColor: themeStyles.bg,
        },
      };

      return (
        <ReactReader
          url={url}
          location={location}
          locationChanged={locationChanged}
          tocChanged={tocChanged}
          readerStyles={customStyles}
          getRendition={(rendition) => {
            rendition.hooks.content.register((contents: any) => {
              contents.addStylesheetRules({
                'body, p, span, div, h1, h2, h3, h4, h5, h6, li, a, td, th': {
                  'color': `${themeStyles.color} !important`,
                  'background-color': 'transparent !important',
                },
              });
            });
          }}
        />
      );
    };
  },
  {
    ssr: false,
    loading: () => (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#aaa', fontSize: '1.1rem' }}>
        📖 Loading EPUB Reader...
      </div>
    ),
  }
);

interface EpubReaderModalProps {
  book: {
    id: number;
    title: string;
    author: string;
    filePath?: string;
  };
  onClose: () => void;
}

type ReaderTheme = 'dark' | 'light' | 'sepia';

export default function EpubReaderModal({ book, onClose }: EpubReaderModalProps) {
  const [location, setLocation] = useState<string | number>(0);
  const [theme, setTheme] = useState<ReaderTheme>('dark');
  const [epubBuffer, setEpubBuffer] = useState<ArrayBuffer | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Fetch EPUB as ArrayBuffer so epubjs parses in-memory binary without making /META-INF/container.xml 404 requests
  useEffect(() => {
    let isMounted = true;
    const fetchEpub = async () => {
      setIsLoading(true);
      setErrorMsg(null);
      try {
        const fileUrl = `http://127.0.0.1:8000/api/v1/books/${book.id}/file/book.epub`;
        const res = await fetch(fileUrl);
        if (!res.ok) {
          throw new Error(`Server returned HTTP status ${res.status}`);
        }
        const buffer = await res.arrayBuffer();
        if (isMounted) {
          setEpubBuffer(buffer);
        }
      } catch (err: any) {
        console.error('EPUB fetch error:', err);
        if (isMounted) {
          setErrorMsg(err.message || 'Failed to load EPUB file');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    fetchEpub();
    return () => {
      isMounted = false;
    };
  }, [book.id]);

  // Keyboard shortcut listener (Esc key to close)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const locationChanged = (epubcifi: string | number) => {
    setLocation(epubcifi);
  };

  const getThemeStyles = () => {
    switch (theme) {
      case 'light':
        return { bg: '#ffffff', color: '#111111' };
      case 'sepia':
        return { bg: '#f4ecd8', color: '#5b4636' };
      case 'dark':
      default:
        return { bg: '#141414', color: '#e0e0e0' };
    }
  };

  const themeStyles = getThemeStyles();

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.94)',
        backdropFilter: 'blur(8px)',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Top Header Navigation */}
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.85rem 1.5rem',
          backgroundColor: '#18181b',
          borderBottom: '1px solid #27272a',
          color: '#fff',
          zIndex: 10,
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: '#f4f4f5' }}>
            {book.title}
          </h3>
          <span style={{ fontSize: '0.8rem', color: '#a1a1aa' }}>by {book.author}</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {/* Theme Selector */}
          <div style={{ display: 'flex', background: '#27272a', padding: '3px', borderRadius: '6px', gap: '2px' }}>
            <button
              onClick={() => setTheme('dark')}
              style={{
                padding: '4px 10px',
                fontSize: '0.75rem',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                background: theme === 'dark' ? '#3b82f6' : 'transparent',
                color: '#fff',
                fontWeight: theme === 'dark' ? 600 : 400
              }}
            >
              🌙 Dark
            </button>
            <button
              onClick={() => setTheme('sepia')}
              style={{
                padding: '4px 10px',
                fontSize: '0.75rem',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                background: theme === 'sepia' ? '#d97706' : 'transparent',
                color: '#fff',
                fontWeight: theme === 'sepia' ? 600 : 400
              }}
            >
              📜 Sepia
            </button>
            <button
              onClick={() => setTheme('light')}
              style={{
                padding: '4px 10px',
                fontSize: '0.75rem',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                background: theme === 'light' ? '#e4e4e7' : 'transparent',
                color: theme === 'light' ? '#111' : '#fff',
                fontWeight: theme === 'light' ? 600 : 400
              }}
            >
              ☀️ Light
            </button>
          </div>

          {/* Close Button */}
          <button
            onClick={onClose}
            style={{
              background: 'rgba(239, 68, 68, 0.2)',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              color: '#ef4444',
              borderRadius: '6px',
              padding: '6px 14px',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            ✕ Close
          </button>
        </div>
      </header>

      {/* Main Reader View */}
      <div
        style={{
          flex: 1,
          width: '100%',
          maxHeight: 'calc(100vh - 60px)',
          backgroundColor: themeStyles.bg,
          position: 'relative',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center'
        }}
      >
        {isLoading ? (
          <div style={{ color: '#a1a1aa', fontSize: '1.1rem', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <span>⏳</span> Loading book bytes into memory...
          </div>
        ) : errorMsg ? (
          <div style={{ color: '#ef4444', textAlign: 'center', padding: '2rem' }}>
            <h3>Failed to open EPUB</h3>
            <p style={{ color: '#a1a1aa', marginTop: '0.5rem' }}>{errorMsg}</p>
          </div>
        ) : epubBuffer ? (
          <div style={{ height: '100%', width: '100%', maxWidth: '960px', position: 'relative' }}>
            <ReactReaderComponent
              url={epubBuffer}
              location={location}
              locationChanged={locationChanged}
              themeStyles={themeStyles}
            />
          </div>
        ) : null}
      </div>
    </div>
  );
}
