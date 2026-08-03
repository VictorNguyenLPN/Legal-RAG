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
      setQuery('');
    }
  };

  return (
    <div className="search-container">
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
          {loading ? 'Đang trả lời...' : 'Gửi'}
        </button>
      </form>
    </div>
  );
};
