'use client';
import { useState, useRef, useEffect } from 'react';

type Message = {
  id: string;
  sender: 'user' | 'bot';
  text: string;
  isLoading?: boolean;
  trace?: {
    agentPath: string[];
    confidenceScore: number;
    hallucinationGrade: string;
    sources: Array<{ content: string; metadata: any }>;
  };
};

interface ChatWidgetProps {
  selectedBooks: string[];
}

export default function ChatWidget({ selectedBooks }: ChatWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [inputText, setInputText] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'greeting',
      sender: 'bot',
      text: 'Good day! I am your Librarian. Ask me anything about the books in your collection, or beyond.',
    }
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isOpen]);

  const toggleChat = () => setIsOpen(!isOpen);

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!inputText.trim()) return;

    const userText = inputText;
    const userMsg: Message = { id: Date.now().toString(), sender: 'user', text: userText };

    // Add loading placeholder for bot
    const botLoadingId = (Date.now() + 1).toString();
    const botLoadingMsg: Message = {
      id: botLoadingId,
      sender: 'bot',
      text: 'Consulting the archives and library agents...',
      isLoading: true
    };

    setMessages(prev => [...prev, userMsg, botLoadingMsg]);
    setInputText('');

    try {
      const response = await fetch('http://127.0.0.1:8000/api/v1/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: userText,
          selected_books: selectedBooks,
        }),
      });

      if (!response.ok) {
        throw new Error('Query failed');
      }

      const data = await response.json();

      setMessages(prev => prev.map(msg => {
        if (msg.id === botLoadingId) {
          return {
            id: botLoadingId,
            sender: 'bot',
            text: data.answer || 'No answer generated.',
            trace: {
              agentPath: data.agent_path || [],
              confidenceScore: data.confidence_score !== undefined ? data.confidence_score : 0,
              hallucinationGrade: data.hallucination_grade || 'FAIL',
              sources: data.sources || [],
            }
          };
        }
        return msg;
      }));
    } catch (error) {
      console.error(error);
      setMessages(prev => prev.map(msg => {
        if (msg.id === botLoadingId) {
          return {
            id: botLoadingId,
            sender: 'bot',
            text: 'I apologize, but my agent system encountered an error. Please verify the backend is running.',
          };
        }
        return msg;
      }));
    }
  };

  return (
    <div className="chat-widget">
      <div
        className={`chat-window ${isOpen ? 'open' : ''}`}
      >
        <div className="chat-header">
          <span>The Librarian</span>
          {selectedBooks.length > 0 && (
            <span style={{ fontSize: '0.75rem', opacity: 0.8, fontWeight: 'normal' }}>
              ({selectedBooks.length} Books Active)
            </span>
          )}
          <button className="chat-close" onClick={toggleChat}>&times;</button>
        </div>

        <div className="chat-messages">
          {messages.map((msg) => (
            <div key={msg.id} style={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
              <div className={`message ${msg.sender} ${msg.isLoading ? 'loading-pulse' : ''}`}>
                {msg.text}
              </div>

              {msg.trace && (
                <div className="trace-container">
                  <details className="agent-trace-details">
                    <summary className="agent-trace-summary">✧ Agent Trace & Context</summary>
                    <div className="agent-trace-content">
                      <div className="trace-metric-row">
                        <span className="trace-metric-label">Route Path:</span>
                        <div className="trace-path-badges">
                          {msg.trace.agentPath.map((pathItem, pIdx) => (
                            <span key={pIdx} className="trace-path-badge">{pathItem}</span>
                          ))}
                        </div>
                      </div>

                      <div className="trace-metric-row">
                        <span className="trace-metric-label">Hallucination Shield:</span>
                        <span className={`trace-grade-badge ${msg.trace.hallucinationGrade.toLowerCase() === 'pass' ? 'pass' : 'fail'}`}>
                          🛡️ {msg.trace.hallucinationGrade}
                        </span>
                      </div>

                      <div className="trace-metric-row">
                        <span className="trace-metric-label">Confidence:</span>
                        <div className="trace-bar-container">
                          <div className="trace-bar-bg">
                            <div className="trace-bar-fill" style={{ width: `${msg.trace.confidenceScore * 100}%` }}></div>
                          </div>
                          <span className="trace-confidence-num">{Math.round(msg.trace.confidenceScore * 100)}%</span>
                        </div>
                      </div>

                      {msg.trace.sources && msg.trace.sources.length > 0 && (
                        <div className="trace-sources-section">
                          <h4 style={{ fontSize: '0.8rem', margin: '0.5rem 0 0.25rem 0', fontFamily: 'Inter, sans-serif' }}>
                            Retrieved Context:
                          </h4>
                          {msg.trace.sources.map((src, sIdx) => (
                            <div key={sIdx} className="trace-source-item">
                              <p className="trace-source-text">"{src.content}"</p>
                              <div className="trace-source-meta">
                                <span>📖 {src.metadata?.title || 'Unknown Document'}</span>
                                {src.metadata?.page !== undefined && src.metadata.page !== 0 && (
                                  <span>Page: {src.metadata.page}</span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </details>
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <form className="chat-input-area" onSubmit={handleSend}>
          <input
            type="text"
            className="chat-input"
            placeholder={selectedBooks.length > 0 ? "Ask selected books a question..." : "Ask a general question..."}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
          />
          <button type="submit" className="chat-send">
            ➤
          </button>
        </form>
      </div>

      <div className="chat-trigger" onClick={toggleChat} title="Open Chat">
        {isOpen ? '✕' : '💬'}
      </div>
    </div>
  );
}

