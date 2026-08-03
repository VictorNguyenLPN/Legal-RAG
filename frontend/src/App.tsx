import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Sidebar } from './components/Sidebar';
import type { DBStatus } from './components/Sidebar';
import { Header } from './components/Header';
import { SearchForm } from './components/SearchForm';
import type { Source } from './components/Citations';
import { SourceDetails } from './components/SourceDetails';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
}

interface Toast {
  message: string;
  type: 'success' | 'error' | 'info';
}

function App() {
  const [dbStatus, setDbStatus] = useState<DBStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [toast, setToast] = useState<Toast | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Show toast notification
  const showToast = (message: string, type: 'success' | 'error' | 'info') => {
    setToast({ message, type });
  };

  // Clear toast after 4s
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => {
        setToast(null);
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  // Fetch Database Status
  const fetchStatus = async (showLoading = false) => {
    if (showLoading) setLoadingStatus(true);
    try {
      const res = await fetch(`${API_URL}/status`);
      if (res.ok) {
        const data = await res.json();
        setDbStatus(data);
      } else {
        setDbStatus(null);
      }
    } catch (err) {
      setDbStatus(null);
    } finally {
      if (showLoading) setLoadingStatus(false);
    }
  };

  // Poll database status every 5 seconds
  useEffect(() => {
    fetchStatus();
    const interval = setInterval(() => {
      fetchStatus();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleRefreshStatus = () => {
    fetchStatus(true);
    showToast('Đang cập nhật trạng thái hệ thống...', 'info');
  };

  // Ingest custom JSON file contents
  const handleIngestCustom = async (chunks: any[]) => {
    setIngesting(true);
    showToast('Đang tải lên và nhúng dữ liệu...', 'info');
    try {
      const res = await fetch(`${API_URL}/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(chunks),
      });
      if (res.status === 201) {
        showToast(`Lập chỉ mục thành công ${chunks.length} chunks!`, 'success');
        fetchStatus();
      } else {
        const errorData = await res.json().catch(() => ({}));
        showToast(`Lỗi: ${errorData.detail || 'Không rõ'}`, 'error');
      }
    } catch (err) {
      showToast('Không thể kết nối tới máy chủ để tải lên.', 'error');
    } finally {
      setIngesting(false);
    }
  };

  // Execute query RAG search (send chat message)
  const handleSearch = async (searchQuery: string) => {
    if (!dbStatus || !dbStatus.database_initialized) {
      showToast('Thư viện pháp luật chưa được lập chỉ mục. Vui lòng nạp dữ liệu trước.', 'error');
      return;
    }

    const userMsgId = Date.now().toString();
    const assistantMsgId = (Date.now() + 1).toString();

    // 1. Add user message
    const newUserMsg: ChatMessage = {
      id: userMsgId,
      role: 'user',
      content: searchQuery
    };

    setMessages((prev) => [...prev, newUserMsg]);
    setLoadingSearch(true);

    try {
      // Format chat history (excluding the message we're currently sending)
      const historyPayload = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 45000);

      const res = await fetch(`${API_URL}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: searchQuery,
          history: historyPayload
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (res.ok) {
        const data = await res.json();
        const newAssistantMsg: ChatMessage = {
          id: assistantMsgId,
          role: 'assistant',
          content: data.answer || 'Không tìm thấy câu trả lời phù hợp.',
          sources: data.sources || []
        };
        setMessages((prev) => [...prev, newAssistantMsg]);
      } else {
        const errorData = await res.json().catch(() => ({}));
        const newErrorMsg: ChatMessage = {
          id: assistantMsgId,
          role: 'assistant',
          content: `**Lỗi hệ thống:** ${errorData.detail || 'Phản hồi thất bại từ máy chủ.'}`
        };
        setMessages((prev) => [...prev, newErrorMsg]);
      }
    } catch (err: any) {
      let message = 'Không thể kết nối tới dịch vụ phân tích. Vui lòng kiểm tra lại backend.';
      if (err.name === 'AbortError') {
        message = 'Thời gian phản hồi từ máy chủ quá hạn. Vui lòng thử lại sau.';
      }

      const newErrorMsg: ChatMessage = {
        id: assistantMsgId,
        role: 'assistant',
        content: `**Lỗi kết nối:** ${message}`
      };
      setMessages((prev) => [...prev, newErrorMsg]);
      showToast(message, 'error');
    } finally {
      setLoadingSearch(false);
    }
  };

  // Reset chat history
  const handleResetChat = () => {
    setMessages([]);
    showToast('Đã làm mới cuộc hội thoại.', 'success');
  };

  // Auto scroll to bottom of chat
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loadingSearch]);

  return (
    <div className="app-container">
      {/* Sidebar Controls */}
      <Sidebar
        dbStatus={dbStatus}
        loadingStatus={loadingStatus}
        onRefreshStatus={handleRefreshStatus}
        onIngestCustom={handleIngestCustom}
        ingesting={ingesting}
        onResetChat={handleResetChat}
        chatLength={messages.length}
      />

      {/* Main Panel */}
      <div className="main-panel" style={{ display: 'flex', flexDirection: 'column', height: '100vh'}}>
        {messages.length === 0 && <Header />}

        {/* Chat / Content Area */}
        <div style={{ flexGrow: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1rem', minHeight: 0}}>

          {messages.length === 0 ? (
            <></>
          ) : (
            <div className="chat-history-container" style={{ maxHeight: 'none', flexGrow: 1, border: 'none', background: 'transparent'}}>
              {messages.map((msg) => (
                <div key={msg.id} className={`chat-message-item ${msg.role}`}>
                  <div className={`chat-bubble ${msg.role}`}>
                    {msg.role === 'user' ? (
                      <div>{msg.content}</div>
                    ) : (
                      <div className="legal-opinion-text" style={{ fontFamily: 'var(--font-serif)', fontSize: '1.1rem', lineHeight: '1.7' }}>
                        <ReactMarkdown>{msg.content}</ReactMarkdown>

                        {msg.sources && msg.sources.length > 0 && (
                          <div className="chat-sources-wrapper">
                            <SourceDetails sources={msg.sources} />
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {loadingSearch && (
                <div className="chat-message-item assistant">
                  <div className="chat-bubble assistant" style={{ display: 'flex', alignItems: 'center', gap: '12px', width: 'auto' }}>
                    <div className="spinner" style={{ width: '20px', height: '20px', borderWidth: '2px', margin: 0 }}></div>
                    <span style={{ color: 'var(--color-text-muted)', fontSize: '0.95rem', fontFamily: 'var(--font-serif)', fontStyle: 'italic' }}>
                      Đang suy nghĩ ...
                    </span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Form at Bottom */}
        <SearchForm
          onSearch={handleSearch}
          loading={loadingSearch}
          disabled={dbStatus === null || !dbStatus.database_initialized}
          initialQuery=""
        />
      </div>

      {/* Floating Toast Notification */}
      {toast && (
        <div className="toast-msg">
          <span>⚖️</span>
          <span>{toast.message}</span>
        </div>
      )}
    </div>
  );
}

export default App;
