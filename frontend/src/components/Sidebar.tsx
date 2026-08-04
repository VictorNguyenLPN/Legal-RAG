import React, { useRef, useState } from 'react';
import { Upload, FileJson, X, RefreshCw, Trash2, MessageSquare, Plus, Edit2, Check } from 'lucide-react';

export interface DBStatus {
  database_initialized: boolean;
  chunk_count: number;
  has_embeddings: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  messages: any[];
  createdAt: number;
}

interface SidebarProps {
  dbStatus: DBStatus | null;
  loadingStatus: boolean;
  onRefreshStatus: () => void;
  onIngestCustom: (chunks: any[]) => Promise<void>;
  ingesting: boolean;
  conversations: Conversation[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onDeleteConversation: (id: string, e: React.MouseEvent) => void;
  onRenameConversation: (id: string, newTitle: string) => void;
  onNewChat: () => void;
  onClearAllConversations: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  dbStatus,
  loadingStatus,
  onRefreshStatus,
  onIngestCustom,
  ingesting,
  conversations,
  activeConversationId,
  onSelectConversation,
  onDeleteConversation,
  onRenameConversation,
  onNewChat,
  onClearAllConversations,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [parsedChunks, setParsedChunks] = useState<any[] | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState<string>('');

  const startEditing = (id: string, currentTitle: string) => {
    setEditingId(id);
    setEditingTitle(currentTitle);
  };

  const handleSaveRename = (id: string) => {
    if (editingTitle.trim()) {
      onRenameConversation(id, editingTitle.trim());
    }
    setEditingId(null);
    setEditingTitle('');
  };

  const handleCancelRename = () => {
    setEditingId(null);
    setEditingTitle('');
  };

  const getBackendStatus = () => {
    if (dbStatus !== null) {
      return { dotClass: 'active', text: 'OK' };
    }
    if (ingesting) {
      return { dotClass: 'ingesting', text: 'Đang xử lý...' };
    }
    return { dotClass: 'inactive', text: 'Disconnected' };
  };

  const getDbStatusInfo = () => {
    if (ingesting) {
      return { dotClass: 'ingesting', text: 'Đang nạp dữ liệu...' };
    }
    if (dbStatus !== null) {
      if (dbStatus.database_initialized) {
        return { dotClass: 'active', text: `${dbStatus.chunk_count} Chunks` };
      }
      return { dotClass: 'inactive', text: 'No Data' };
    }
    return { dotClass: 'inactive', text: 'Disconnected' };
  };

  const backendStatus = getBackendStatus();
  const dbStatusInfo = getDbStatusInfo();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setErrorMsg(null);
    const files = e.target.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file.type !== 'application/json' && !file.name.endsWith('.json')) {
        setErrorMsg('Vui lòng chọn tập tin định dạng JSON.');
        return;
      }
      setSelectedFile(file);
      const reader = new FileReader();
      reader.onload = (event) => {
        try {
          const json = JSON.parse(event.target?.result as string);
          if (!Array.isArray(json)) {
            setErrorMsg('Nội dung file JSON phải là một mảng các chunk.');
            setParsedChunks(null);
            return;
          }
          setParsedChunks(json);
        } catch (err) {
          setErrorMsg('Lỗi phân tích cú pháp JSON: File không hợp lệ.');
          setParsedChunks(null);
        }
      };
      reader.readAsText(file);
    }
  };

  const handleIngestCustomClick = async () => {
    if (parsedChunks) {
      await onIngestCustom(parsedChunks);
      // Clear selected file upon success
      setSelectedFile(null);
      setParsedChunks(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleRemoveFile = (e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedFile(null);
    setParsedChunks(null);
    setErrorMsg(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="sidebar">
      {/* System Status Section */}
      <div className="sidebar-section">
        <div className="sidebar-header flex-header">
          <span>Trạng Thái Hệ Thống</span>
          <button 
            onClick={onRefreshStatus} 
            disabled={loadingStatus}
            className="btn-refresh"
            title="Làm mới trạng thái"
          >
            <RefreshCw 
              size={14} 
              className={`spin-icon ${loadingStatus ? 'loading' : ''}`} 
            />
          </button>
        </div>

        <div className="status-box">
          <div className="status-line">
            <span className={`status-dot ${backendStatus.dotClass}`}></span>
            <span>Backend: {backendStatus.text}</span>
          </div>
          <div className="status-line">
            <span className={`status-dot ${dbStatusInfo.dotClass}`}></span>
            <span>Database: {dbStatusInfo.text}</span>
          </div>
        </div>
      </div>

      {/* Ingest Section */}
      <div className="sidebar-section">
        <div className="sidebar-header">Nhập Tài Liệu Pháp Lý</div>
        <p className="sidebar-desc">
          Embedding tài liệu pháp lý thành Vector và lưu vào ChromaDB.
        </p>

        {/* Custom JSON Upload */}
        <div className="sidebar-upload-container">
          <p className="sidebar-upload-label">
            Tải lên tập tin mới
          </p>
          
          <input 
            type="file" 
            accept=".json" 
            ref={fileInputRef} 
            onChange={handleFileChange} 
            className="hidden-input"
          />

          {!selectedFile ? (
            <div className="file-upload-dropzone" onClick={() => fileInputRef.current?.click()}>
              <Upload className="file-upload-icon" />
              <div className="file-upload-text">Chọn tệp JSON</div>
              <div className="file-upload-subtext">Nhấn vào đây để tải lên</div>
            </div>
          ) : (
            <div className="file-selected-box">
              <div className="file-selected-info">
                <div className="file-selected-left">
                  <FileJson size={18} className="file-json-icon" />
                  <span className="file-name" title={selectedFile.name}>{selectedFile.name}</span>
                </div>
                <button className="btn-remove-file" onClick={handleRemoveFile}>
                  <X size={16} />
                </button>
              </div>
              <div className="file-upload-subtext file-selected-subtext">
                {parsedChunks ? `${parsedChunks.length} chunks sẵn sàng` : 'Đang tải...'}
              </div>
              {parsedChunks && (
                <button 
                  className="btn-gold-outline btn-ingest-file" 
                  onClick={handleIngestCustomClick}
                  disabled={ingesting}
                >
                  {ingesting ? 'Đang lập chỉ mục...' : 'Lập chỉ mục tệp này'}
                </button>
              )}
            </div>
          )}

          {errorMsg && (
            <p style={{ fontSize: '0.8rem', color: 'var(--color-danger)', marginTop: '0.25rem' }}>
              {errorMsg}
            </p>
          )}
        </div>
      </div>

      {/* Conversations History Section */}
      <div className="sidebar-section conversations-section">
        <div className="sidebar-header flex-header">
          <span>Lịch Sử Hội Thoại</span>
          <button 
            onClick={onNewChat}
            className="btn-refresh"
            title="Tạo cuộc hội thoại mới"
          >
            <Plus size={16} />
          </button>
        </div>

        <button 
          className="btn-gold-outline btn-new-chat"
          onClick={onNewChat}
        >
          <Plus size={16} />
          <span>Hội thoại mới</span>
        </button>

        {conversations.length === 0 ? (
          <p className="sidebar-desc" style={{ textAlign: 'center', fontStyle: 'italic' }}>
            Chưa có cuộc hội thoại nào.
          </p>
        ) : (
          <div className="conversations-list">
            {conversations.map((conv) => {
              const isActive = conv.id === activeConversationId;
              const isEditing = conv.id === editingId;

              return (
                <div 
                  key={conv.id} 
                  className={`conversation-item ${isActive ? 'active' : ''}`}
                  onClick={() => !isEditing && onSelectConversation(conv.id)}
                >
                  <div className="conversation-item-left">
                    <MessageSquare size={14} className="file-json-icon" style={{ flexShrink: 0 }} />
                    {isEditing ? (
                      <input
                        type="text"
                        value={editingTitle}
                        onChange={(e) => setEditingTitle(e.target.value)}
                        className="conversation-rename-input"
                        autoFocus
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleSaveRename(conv.id);
                          if (e.key === 'Escape') handleCancelRename();
                        }}
                        onClick={(e) => e.stopPropagation()}
                        onBlur={() => handleSaveRename(conv.id)}
                      />
                    ) : (
                      <span className="conversation-item-title" title={conv.title}>
                        {conv.title}
                      </span>
                    )}
                  </div>
                  
                  {!isEditing && (
                    <div className="conversation-item-actions">
                      <button 
                        className="btn-conv-action"
                        onClick={(e) => {
                          e.stopPropagation();
                          startEditing(conv.id, conv.title);
                        }}
                        title="Đổi tên"
                      >
                        <Edit2 size={12} />
                      </button>
                      <button 
                        className="btn-conv-action delete"
                        onClick={(e) => onDeleteConversation(conv.id, e)}
                        title="Xóa"
                      >
                        <X size={12} />
                      </button>
                    </div>
                  )}

                  {isEditing && (
                    <div className="conversation-item-actions" style={{ display: 'flex' }}>
                      <button 
                        className="btn-conv-action"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSaveRename(conv.id);
                        }}
                        title="Lưu"
                      >
                        <Check size={12} />
                      </button>
                      <button 
                        className="btn-conv-action delete"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCancelRename();
                        }}
                        title="Hủy"
                      >
                        <X size={12} />
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Reset/Clean Section */}
      <div className="sidebar-section bottom">
        <button 
          className={`btn-gold-outline btn-reset-chat ${conversations.length > 0 ? 'active' : ''}`} 
          onClick={onClearAllConversations}
          disabled={conversations.length === 0}
        >
          <Trash2 size={16} />
          <span>Xóa tất cả hội thoại</span>
        </button>
      </div>
    </div>
  );
};
