import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import type { Source } from './Citations';

interface SourceDetailsProps {
  sources: Source[];
}

export const SourceDetails: React.FC<SourceDetailsProps> = ({ sources }) => {
  const [expandedIndices, setExpandedIndices] = useState<Record<number, boolean>>({});

  if (!sources || sources.length === 0) return null;

  const toggleExpand = (index: number) => {
    setExpandedIndices((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  return (
    <div>
      <h3 className="source-section-title">Nguồn Trích Dẫn</h3>
      <div className="accordion-list">
        {sources.map((src, idx) => {
          const isExpanded = !!expandedIndices[idx];
          const doc = src.document_title || 'N/A';
          const art = src.article_title || (src.article_number ? `Điều ${src.article_number}` : 'N/A');
          const clause = src.clause_number ? `Khoản ${src.clause_number}` : '';
          const point = src.point ? `Điểm ${src.point}` : '';
          const score = src.rrf_score || 0;

          return (
            <div 
              key={src.chunk_id || idx} 
              className={`accordion-item ${isExpanded ? 'expanded' : ''}`}
            >
              <div className="accordion-header" onClick={() => toggleExpand(idx)}>
                <div className="accordion-header-left">
                  <span className="accordion-badge">{idx + 1}</span>
                  <span className="accordion-title-text">
                    {art} - {doc}
                  </span>
                </div>
                <ChevronDown className="accordion-arrow" />
              </div>
              <div className="accordion-content">
                <div className="chunk-card">
                  <div className="chunk-text">{src.text}</div>
                  <div className="chunk-meta">
                    <span>
                      Chunk ID: <code>{src.chunk_id}</code>
                    </span>
                    <span>
                      Vị trí: {clause || 'N/A'} | {point || 'N/A'}
                    </span>
                    <span>
                      RRF Score: <code>{score.toFixed(6)}</code>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
