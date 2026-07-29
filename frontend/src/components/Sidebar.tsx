import React, { useRef, useState } from 'react';
import { Upload, FileJson, X, RefreshCw } from 'lucide-react';

export interface DBStatus {
  database_initialized: boolean;
  chunk_count: number;
  has_embeddings: boolean;
}

interface SidebarProps {
  dbStatus: DBStatus | null;
  loadingStatus: boolean;
  onRefreshStatus: () => void;
  onIngestDemo: () => Promise<void>;
  onIngestCustom: (chunks: any[]) => Promise<void>;
  ingesting: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  dbStatus,
  loadingStatus,
  onRefreshStatus,
  onIngestDemo,
  onIngestCustom,
  ingesting,
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
              <span>Backend: Mất kết nối</span>
            </div>
            <div className="status-subtext">
              Hãy chắc chắn cổng 8000 đang được mở và ứng dụng backend đang hoạt động.
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

        {/* Demo Chunk */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.5rem' }}>
          <p style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--color-gold)', marginBottom: '2px' }}>
            Nạp dữ liệu
          </p>
          <button 
            className="btn-gold-outline" 
            onClick={onIngestDemo}
            disabled={ingesting || dbStatus === null}
          >
            {ingesting ? 'Đang xử lý...' : 'Ingestion'}
          </button>
        </div>

        <hr style={{ borderColor: 'rgba(255, 255, 255, 0.1)', margin: '0.75rem 0' }} />

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
