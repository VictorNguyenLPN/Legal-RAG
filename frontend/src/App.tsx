import { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import type { DBStatus } from './components/Sidebar';
import { Header } from './components/Header';
import { SearchForm } from './components/SearchForm';
import { AnswerCard } from './components/AnswerCard';
import { Citations } from './components/Citations';
import type { Source } from './components/Citations';
import { SourceDetails } from './components/SourceDetails';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const DEMO_FILE_PATH = '/home/nguyen-quang-huy/Github/Law-RAG/demo_chunk.json';

interface SearchResult {
  answer?: string;
  sources?: Source[];
  error?: string;
  status?: 'empty_db';
}

interface Toast {
  message: string;
  type: 'success' | 'error' | 'info';
}

function App() {
  const [dbStatus, setDbStatus] = useState<DBStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [query, setQuery] = useState('');
  const [searchResult, setSearchResult] = useState<SearchResult | null>(null);
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [toast, setToast] = useState<Toast | null>(null);

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

  // Ingest demo_chunk.json
  const handleIngestDemo = async () => {
    setIngesting(true);
    showToast('Đang xử lý & phân mảnh demo_chunk.json...', 'info');
    try {
      const res = await fetch(`${API_URL}/ingest-file`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: DEMO_FILE_PATH }),
      });
      if (res.status === 201) {
        showToast('Nạp dữ liệu demo thành công!', 'success');
        fetchStatus();
      } else {
        const errorData = await res.json().catch(() => ({}));
        showToast(`Lỗi: ${errorData.detail || 'Không rõ'}`, 'error');
      }
    } catch (err) {
      showToast('Đã xảy ra lỗi khi kết nối tới máy chủ.', 'error');
    } finally {
      setIngesting(false);
    }
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

  // Execute query RAG search
  const handleSearch = async (searchQuery: string) => {
    setQuery(searchQuery);
    if (!dbStatus || !dbStatus.database_initialized) {
      setSearchResult({ status: 'empty_db' });
      return;
    }

    setLoadingSearch(true);
    setSearchResult(null);
    try {
      // Set a 45 second timeout simulation
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 45000);

      const res = await fetch(`${API_URL}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (res.ok) {
        const data = await res.json();
        setSearchResult(data);
      } else {
        const errorData = await res.json().catch(() => ({}));
        setSearchResult({ 
          error: `Yêu cầu thất bại: ${errorData.detail || 'Không rõ lỗi'}` 
        });
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        setSearchResult({ 
          error: 'Thời gian phản hồi từ máy chủ quá hạn. Vui lòng thử lại sau.' 
        });
      } else {
        setSearchResult({ 
          error: 'Không thể kết nối tới dịch vụ phân tích. Vui lòng kiểm tra lại backend.' 
        });
      }
    } finally {
      setLoadingSearch(false);
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar Controls */}
      <Sidebar
        dbStatus={dbStatus}
        loadingStatus={loadingStatus}
        onRefreshStatus={handleRefreshStatus}
        onIngestDemo={handleIngestDemo}
        onIngestCustom={handleIngestCustom}
        ingesting={ingesting}
      />

      {/* Main Panel */}
      <div className="main-panel">
        <Header />
        
        <SearchForm 
          onSearch={handleSearch} 
          loading={loadingSearch} 
          disabled={dbStatus === null}
          initialQuery={query}
        />

        {/* Dynamic Display Area */}
        {loadingSearch && (
          <div className="loader-container">
            <div className="spinner"></div>
            <div className="loader-text">Hệ thống đang đối chiếu cơ sở dữ liệu pháp luật...</div>
          </div>
        )}

        {!loadingSearch && query && (
          <div>
            {searchResult?.status === 'empty_db' && (
              <div className="tip-box warning">
                <div className="tip-icon danger">⚠️</div>
                <div className="tip-title danger">Dữ liệu trống</div>
                <div className="tip-desc">
                  Thư viện pháp luật chưa được lập chỉ mục. Hãy nạp tài liệu từ thanh quản lý bên trái để tiếp tục.
                </div>
              </div>
            )}

            {searchResult?.error && (
              <div className="tip-box warning">
                <div className="tip-icon danger">⚠️</div>
                <div className="tip-title danger">Lỗi hệ thống</div>
                <div className="tip-desc">{searchResult.error}</div>
              </div>
            )}

            {searchResult && !searchResult.error && searchResult.status !== 'empty_db' && (
              <div>
                {searchResult.answer && <AnswerCard answer={searchResult.answer} />}
                {searchResult.sources && <Citations sources={searchResult.sources} />}
                {searchResult.sources && <SourceDetails sources={searchResult.sources} />}
              </div>
            )}
          </div>
        )}

        {!loadingSearch && !query && (
          <div>
            {dbStatus && dbStatus.database_initialized ? (
              <div className="tip-box">
                <div className="tip-icon">⚖️</div>
                <div className="tip-title">Hệ Thống Đã Sẵn Sàng</div>
                <div className="tip-desc">
                  Vui lòng nhập câu hỏi pháp lý của bạn ở thanh công cụ phía trên. Trợ lý sẽ tự động tìm kiếm điều khoản phù hợp và đưa ra phân tích chi tiết.
                </div>
              </div>
            ) : (
              <div className="tip-box warning">
                <div className="tip-icon danger">⚠️</div>
                <div className="tip-title danger">Thiếu Cơ Sở Dữ Liệu</div>
                <div className="tip-desc">
                  Vui lòng nhấn nút <strong>"Tải demo_chunk.json"</strong> ở thanh quản lý bên trái để nạp dữ liệu mẫu trước khi đặt câu hỏi.
                </div>
              </div>
            )}
          </div>
        )}
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
