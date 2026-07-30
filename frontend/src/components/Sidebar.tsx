import React, { useRef, useState } from 'react';
import { Upload, FileJson, X, RefreshCw, Trash2 } from 'lucide-react';

export interface DBStatus {
  database_initialized: boolean;
  chunk_count: number;
  has_embeddings: boolean;
}

interface SidebarProps {
  dbStatus: DBStatus | null;
  loadingStatus: boolean;
  onRefreshStatus: () => void;
  onIngestCustom: (chunks: any[]) => Promise<void>;
  ingesting: boolean;
  onResetChat: () => void;
  chatLength: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  dbStatus,
  loadingStatus,
  onRefreshStatus,
  onIngestCustom,
  ingesting,
  onResetChat,
  chatLength,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [parsedChunks, setParsedChunks] = useState<any[] | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
        <div 
          className="sidebar-header" 
          style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
        >
          <span>Trạng Thái Hệ Thống</span>
          <button 
            onClick={onRefreshStatus} 
            disabled={loadingStatus}
            style={{ 
              background: 'none', 
              border: 'none', 
              color: 'var(--color-gold)', 
              cursor: 'pointer', 
              display: 'flex', 
              alignItems: 'center' 
            }}
            title="Làm mới trạng thái"
          >
            <RefreshCw 
              size={14} 
              style={{ 
                animation: loadingStatus ? 'spin 1s linear infinite' : 'none' 
              }} 
            />
          </button>
        </div>

        {dbStatus === null ? (
          <div className="status-box">
            <div className="status-line">
              <span className="status-dot inactive"></span>
              <span>Backend: Disconnect</span>
            </div>
          </div>
        ) : (
          <div className="status-box">
            <div className="status-line">
              <span className="status-dot active"></span>
              <span>API: Hoạt động (OK)</span>
            </div>
            <div className="status-line">
              <span className={`status-dot ${dbStatus.database_initialized ? 'active' : 'inactive'}`}></span>
              <span>Corpus: {dbStatus.database_initialized ? `${dbStatus.chunk_count} Chunks` : 'Chưa có dữ liệu'}</span>
            </div>
          </div>
        )}
      </div>

      {/* Ingest Section */}
      <div className="sidebar-section">
        <div className="sidebar-header">Nạp Tài Liệu Pháp Lý</div>
        <p className="sidebar-desc">
          Chuyển đổi và lập chỉ mục các văn bản pháp luật dưới dạng Vector và Từ khóa (Hybrid Index).
        </p>

        {/* Custom JSON Upload */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <p style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--color-gold)', marginBottom: '2px' }}>
            Tải lên tập tin mới
          </p>
          
          <input 
            type="file" 
            accept=".json" 
            ref={fileInputRef} 
            onChange={handleFileChange} 
            style={{ display: 'none' }}
          />

          {!selectedFile ? (
            <div className="file-upload-dropzone" onClick={() => fileInputRef.current?.click()}>
              <Upload className="file-upload-icon" />
              <div className="file-upload-text">Chọn tệp cấu trúc JSON</div>
              <div className="file-upload-subtext">Nhấn vào đây để tải lên</div>
            </div>
          ) : (
            <div className="file-selected-box">
              <div className="file-selected-info">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', width: '85%' }}>
                  <FileJson size={18} style={{ color: 'var(--color-gold)', flexShrink: 0 }} />
                  <span className="file-name" title={selectedFile.name}>{selectedFile.name}</span>
                </div>
                <button className="btn-remove-file" onClick={handleRemoveFile}>
                  <X size={16} />
                </button>
              </div>
              <div className="file-upload-subtext" style={{ paddingLeft: '24px' }}>
                {parsedChunks ? `${parsedChunks.length} chunks sẵn sàng` : 'Đang tải...'}
              </div>
              {parsedChunks && (
                <button 
                  className="btn-gold-outline" 
                  onClick={handleIngestCustomClick}
                  disabled={ingesting}
                  style={{ marginTop: '0.5rem', padding: '0.5rem', fontSize: '0.75rem' }}
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

      {/* Conversation Section */}
      <div className="sidebar-section" style={{ marginTop: 'auto' }}>
        <div className="sidebar-header" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* <MessageSquare size={18} style={{ color: 'var(--color-gold)' }} /> */}
          <span>Hội Thoại</span>
        </div>
        <p className="sidebar-desc">
          Lịch sử chat được lưu trữ tạm thời trong phiên làm việc hiện tại.
        </p>
        <button 
          className="btn-gold-outline" 
          onClick={onResetChat}
          disabled={chatLength === 0}
          style={{ 
            marginTop: '0.5rem', 
            borderColor: chatLength > 0 ? 'rgba(239, 68, 68, 0.4)' : 'rgba(197, 168, 128, 0.2)',
            color: chatLength > 0 ? '#FCA5A5' : 'var(--color-text-muted)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px'
          }}
        >
          <Trash2 size={16} />
          <span>Xóa lịch sử chat</span>
        </button>
      </div>
      
      {/* CSS Animation Keyframes for Refresh button */}
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};
