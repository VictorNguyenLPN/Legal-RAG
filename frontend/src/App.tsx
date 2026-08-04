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
  promptTokens?: number;
  responseTokens?: number;
  totalTokens?: number;
  responseTime?: number;
}

interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
}

interface Toast {
  message: string;
  type: 'success' | 'error' | 'info';
}

function App() {
  const [dbStatus, setDbStatus] = useState<DBStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  
  // Conversations list synced with LocalStorage
  const [conversations, setConversations] = useState<Conversation[]>(() => {
    try {
      const saved = localStorage.getItem('law_rag_conversations');
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      console.error("Failed to parse conversations", e);
      return [];
    }
  });

  const [activeConversationId, setActiveConversationId] = useState<string | null>(() => {
    return localStorage.getItem('law_rag_active_conversation_id') || null;
  });

  const [loadingSearch, setLoadingSearch] = useState(false);
  const [toast, setToast] = useState<Toast | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Sync conversations to localStorage
  useEffect(() => {
    localStorage.setItem('law_rag_conversations', JSON.stringify(conversations));
  }, [conversations]);

  // Sync activeConversationId to localStorage
  useEffect(() => {
    if (activeConversationId) {
      localStorage.setItem('law_rag_active_conversation_id', activeConversationId);
    } else {
      localStorage.removeItem('law_rag_active_conversation_id');
    }
  }, [activeConversationId]);

  // Derived active messages
  const activeConv = conversations.find(c => c.id === activeConversationId);
  const messages = activeConv ? activeConv.messages : [];

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

    let targetConvId = activeConversationId;
    let historyPayload: { role: string; content: string }[] = [];

    if (!targetConvId) {
      // Create new conversation
      targetConvId = Date.now().toString();
      const newConv: Conversation = {
        id: targetConvId,
        title: searchQuery.substring(0, 35).trim() + (searchQuery.length > 35 ? '...' : ''),
        messages: [newUserMsg],
        createdAt: Date.now()
      };
      setConversations((prev) => [newConv, ...prev]);
      setActiveConversationId(targetConvId);
      historyPayload = [];
    } else {
      // Append user message to active conversation
      setConversations((prev) =>
        prev.map((c) => {
          if (c.id === targetConvId) {
            historyPayload = c.messages.map(msg => ({
              role: msg.role,
              content: msg.content
            }));
            return {
              ...c,
              messages: [...c.messages, newUserMsg]
            };
          }
          return c;
        })
      );
    }

    setLoadingSearch(true);

    try {
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
          sources: data.sources || [],
          promptTokens: data.prompt_tokens,
          responseTokens: data.response_tokens,
          totalTokens: data.total_tokens,
          responseTime: data.response_time
        };
        setConversations((prev) =>
          prev.map((c) => {
            if (c.id === targetConvId) {
              return {
                ...c,
                messages: [...c.messages, newAssistantMsg]
              };
            }
            return c;
          })
        );
      } else {
        const errorData = await res.json().catch(() => ({}));
        const newErrorMsg: ChatMessage = {
          id: assistantMsgId,
          role: 'assistant',
          content: `**Lỗi hệ thống:** ${errorData.detail || 'Phản hồi thất bại từ máy chủ.'}`
        };
        setConversations((prev) =>
          prev.map((c) => {
            if (c.id === targetConvId) {
              return {
                ...c,
                messages: [...c.messages, newErrorMsg]
              };
            }
            return c;
          })
        );
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
      setConversations((prev) =>
        prev.map((c) => {
          if (c.id === targetConvId) {
            return {
              ...c,
              messages: [...c.messages, newErrorMsg]
            };
          }
          return c;
        })
      );
      showToast(message, 'error');
    } finally {
      setLoadingSearch(false);
    }
  };

  const handleSelectConversation = (id: string) => {
    setActiveConversationId(id);
  };

  const handleDeleteConversation = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const conv = conversations.find(c => c.id === id);
    const convTitle = conv ? ` "${conv.title}"` : '';
    if (window.confirm(`Bạn có chắc chắn muốn xóa cuộc hội thoại${convTitle} không?`)) {
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeConversationId === id) {
        setActiveConversationId(null);
      }
      showToast('Đã xóa cuộc hội thoại.', 'success');
    }
  };

  const handleRenameConversation = (id: string, newTitle: string) => {
    if (!newTitle.trim()) return;
    setConversations((prev) =>
      prev.map((c) => (c.id === id ? { ...c, title: newTitle.trim() } : c))
    );
    showToast('Đã đổi tên cuộc hội thoại.', 'success');
  };

  const handleNewChat = () => {
    setActiveConversationId(null);
    showToast('Bắt đầu cuộc hội thoại mới.', 'success');
  };

  const handleClearAllConversations = () => {
    if (window.confirm('Bạn có chắc chắn muốn xóa toàn bộ lịch sử các cuộc hội thoại không?')) {
      setConversations([]);
      setActiveConversationId(null);
      showToast('Đã xóa toàn bộ lịch sử hội thoại.', 'success');
    }
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
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={handleSelectConversation}
        onDeleteConversation={handleDeleteConversation}
        onRenameConversation={handleRenameConversation}
        onNewChat={handleNewChat}
        onClearAllConversations={handleClearAllConversations}
      />

      {/* Main Panel */}
      <div className="main-panel">
        {messages.length === 0 && <Header />}

        {/* Chat / Content Area */}
        <div className="chat-area-wrapper">

          {messages.length === 0 ? (
            <></>
          ) : (
            <div className="chat-history-container">
              {messages.map((msg) => (
                <div key={msg.id} className={`chat-message-item ${msg.role}`}>
                  <div className={`chat-bubble ${msg.role}`}>
                    {msg.role === 'user' ? (
                      <div>{msg.content}</div>
                    ) : (
                      <div className="legal-opinion-text legal-opinion-chat-text">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>

                        {/* Token usage and response time metadata */}
                        {(msg.responseTime !== undefined || msg.promptTokens !== undefined || msg.responseTokens !== undefined) && (
                          <div className="chat-metadata-bar">
                            {msg.responseTime !== undefined && (
                              <span className="chat-metadata-item time">
                                {msg.responseTime}s
                              </span>
                            )}
                            {msg.promptTokens !== undefined && (
                              <span className="chat-metadata-item">
                                Prompt: {msg.promptTokens} tokens
                              </span>
                            )}
                            {msg.responseTokens !== undefined && (
                              <span className="chat-metadata-item">
                                Response: {msg.responseTokens} tokens
                              </span>
                            )}
                            {msg.totalTokens !== undefined && (
                              <span className="chat-metadata-item total">
                                Total: {msg.totalTokens} tokens
                              </span>
                            )}
                          </div>
                        )}

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
                  <div className="chat-bubble assistant chat-bubble-thinking">
                    <div className="spinner spinner-small"></div>
                    <span className="thinking-text">
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
