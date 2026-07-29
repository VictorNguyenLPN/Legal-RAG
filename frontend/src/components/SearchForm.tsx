import React, { useState, useEffect } from 'react';
import { Search } from 'lucide-react';

interface SearchFormProps {
  onSearch: (query: string) => void;
  loading: boolean;
  disabled: boolean;
  initialQuery: string;
}

export const SearchForm: React.FC<SearchFormProps> = ({
  onSearch,
  loading,
  disabled,
  initialQuery,
}) => {
  const [query, setQuery] = useState(initialQuery);

  // Sync state if query changes externally
  useEffect(() => {
    setQuery(initialQuery);
  }, [initialQuery]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !loading && !disabled) {
      onSearch(query.trim());
    }
  };

  return (
    <div className="search-container">
      <label className="search-label">Nhập câu hỏi pháp lý của bạn:</label>
      <form onSubmit={handleSubmit} className="search-form">
        <div className="search-input-wrapper">
          <Search className="search-icon" />
          <input
            type="text"
            className="search-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ví dụ: Mức hình phạt cao nhất cho tội vô ý làm chết người là bao nhiêu?"
            disabled={loading || disabled}
          />
        </div>
        <button
          type="submit"
          className="btn-search"
          disabled={!query.trim() || loading || disabled}
        >
          {loading ? 'Đang tra cứu...' : 'Tìm kiếm / Tra cứu'}
        </button>
      </form>
      <p 
        style={{ 
          fontSize: '0.8rem', 
          color: 'var(--color-text-muted)', 
          marginTop: '0.5rem', 
          fontStyle: 'italic',
          paddingLeft: '4px' 
        }}
      >
        Nhập tình huống thực tế hoặc điều khoản cần đối chiếu để trợ lý phân tích văn bản pháp luật tương quan.
      </p>
    </div>
  );
};
