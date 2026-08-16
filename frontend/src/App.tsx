import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Sidebar } from './components/Sidebar';
import type { DBStatus } from './components/Sidebar';
import { Header } from './components/Header';
import { SearchForm } from './components/SearchForm';
import type { Source } from './components/SourceDetails';
import { SourceDetails } from './components/SourceDetails';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  tokenDetails?: Record<string, number>;
  timingDetails?: Record<string, number>;
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
  const [loadingStatus, setLoadingStatus] = useState(true);

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
  const [searchPhase, setSearchPhase] = useState<string>('Answering...');
  const [elapsedTime, setElapsedTime] = useState<number>(0);
  const [toast, setToast] = useState<Toast | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleCancelSearch = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort('user_cancelled');
      abortControllerRef.current = null;
    }
  };

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

  // Live Timer for Search Progress
  useEffect(() => {
    let timer: any;
    if (loadingSearch) {
      const startTime = Date.now();
      setSearchPhase('Answering...');
      timer = setInterval(() => {
        const elapsed = (Date.now() - startTime) / 1000;
        setElapsedTime(elapsed);
      }, 100);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [loadingSearch]);

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
      setLoadingStatus(false);
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
    setSearchPhase('Đang nhúng câu truy vấn (Embedding query)...');
    setElapsedTime(0);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const timeoutId = setTimeout(() => controller.abort('timeout'), 45000);

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
          tokenDetails: data.token_details,
          timingDetails: data.timing_details
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
      let isUserCancelled = false;
      let message = 'Không thể kết nối tới dịch vụ phân tích. Vui lòng kiểm tra lại backend.';

      if (err.name === 'AbortError' || controller.signal.aborted) {
        if (controller.signal.reason === 'user_cancelled') {
          isUserCancelled = true;
          message = 'Đã hủy gửi câu hỏi.';
        } else {
          message = 'Thời gian phản hồi từ máy chủ quá hạn. Vui lòng thử lại sau.';
        }
      }

      const newErrorMsg: ChatMessage = {
        id: assistantMsgId,
        role: 'assistant',
        content: isUserCancelled ? '_Đã hủy yêu cầu xử lý câu hỏi._' : `**Lỗi kết nối:** ${message}`
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
      showToast(message, isUserCancelled ? 'info' : 'error');
    } finally {
      abortControllerRef.current = null;
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
                        <>
                          <div className="chat-metadata-bar">
                            {msg.timingDetails && (
                              <span className="chat-metadata-item">
                                Emb & Ret: {msg.timingDetails.search}s | Rerank: {msg.timingDetails.rerank}s | LLM: {msg.timingDetails.llm}s | <b>Total: {msg.timingDetails['total_time']}s</b>
                              </span>
                            )}
                            {msg.tokenDetails !== undefined && (
                              <span className="chat-metadata-item">
                                Prompt: {msg.tokenDetails['prompt_tokens']} tokens | Response: {msg.tokenDetails['response_tokens']} tokens | <b>Total: {msg.tokenDetails['total_tokens']} tokens</b>
                              </span>
                            )}
                          </div>
                        </>

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
                  <div className="chat-bubble assistant chat-bubble-thinking" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '6px', minWidth: '280px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', gap: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div className="spinner spinner-small"></div>
                        <span className="thinking-text" style={{ fontWeight: '600', color: '#1e293b' }}>
                          {searchPhase} ({elapsedTime.toFixed(1)}s)
                        </span>
                      </div>
                    </div>
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
          onCancel={handleCancelSearch}
          loading={loadingSearch}
          disabled={dbStatus === null || !dbStatus.database_initialized}
          initialQuery=""
        />
      </div>

      {/* Floating Toast Notification */}
      {toast && (
        <div className="toast-msg">
          <span>{toast.message}</span>
        </div>
      )}
    </div>
  );
}

export default App;
