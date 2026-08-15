import React, { useState } from 'react';
import { X, RefreshCw, Trash2, MessageSquare, Plus, Edit2, Check } from 'lucide-react';

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
  conversations,
  activeConversationId,
  onSelectConversation,
  onDeleteConversation,
  onRenameConversation,
  onNewChat,
  onClearAllConversations,
}) => {
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
    if (loadingStatus) {
      return { dotClass: 'ingesting', text: 'Đang kết nối...' };
    }
    return { dotClass: 'inactive', text: 'Disconnected' };
  };

  const getDbStatusInfo = () => {
    if (dbStatus !== null) {
      if (dbStatus.database_initialized) {
        return { dotClass: 'active', text: `${dbStatus.chunk_count} Chunks` };
      }
      return { dotClass: 'inactive', text: 'No Data' };
    }
    if (loadingStatus) {
      return { dotClass: 'ingesting', text: 'Đang kết nối...' };
    }
    return { dotClass: 'inactive', text: 'Disconnected' };
  };

  const backendStatus = getBackendStatus();
  const dbStatusInfo = getDbStatusInfo();

  return (
    <div className="sidebar">
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
    </div>
  );
};
