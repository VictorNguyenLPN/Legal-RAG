import React, { useState, useEffect, useRef } from 'react';
import { Square } from 'lucide-react';

interface SearchFormProps {
  onSearch: (query: string) => void;
  onCancel?: () => void;
  loading: boolean;
  disabled: boolean;
  initialQuery: string;
}

export const SearchForm: React.FC<SearchFormProps> = ({
  onSearch,
  onCancel,
  loading,
  disabled,
  initialQuery,
}) => {
  const [query, setQuery] = useState(initialQuery);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Sync state if query changes externally
  useEffect(() => {
    setQuery(initialQuery);
  }, [initialQuery]);

  // Auto resize textarea height and toggle scrollbar
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = `${Math.min(scrollHeight, 180)}px`;
      textareaRef.current.style.overflowY = scrollHeight > 180 ? 'auto' : 'hidden';
    }
  }, [query]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (loading && onCancel) {
      onCancel();
      return;
    }
    if (query.trim() && !loading && !disabled) {
      onSearch(query.trim());
      setQuery('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      if (query.trim() && !loading && !disabled) {
        onSearch(query.trim());
        setQuery('');
      }
    }
  };

  return (
    <div className="search-container">
      <form onSubmit={handleSubmit} className="search-form">
        <div className="search-input-wrapper">
          <textarea
            ref={textareaRef}
            rows={1}
            className="search-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Hỏi bất kỳ điều gì..."
            disabled={disabled}
          />
        </div>
        {loading ? (
          <button
            type="button"
            className="btn-search btn-cancel"
            onClick={onCancel}
            title="Hủy gửi câu hỏi"
          >
            <Square size={14} fill="currentColor" /> Hủy
          </button>
        ) : (
          <button
            type="submit"
            className="btn-search"
            disabled={!query.trim() || disabled}
          >
            Gửi
          </button>
        )}
      </form>
    </div>
  );
};
