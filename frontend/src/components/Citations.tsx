import React from 'react';

export interface Source {
  chunk_id: string;
  document_title: string;
  article_title?: string | null;
  article_number?: number | null;
  clause_number?: any;
  point?: string | null;
  text: string;
  rrf_score: number;
}

interface CitationsProps {
  sources: Source[];
}

export const Citations: React.FC<CitationsProps> = ({ sources }) => {
  if (!sources || sources.length === 0) return null;

  const seenCitations = new Set<string>();
  const uniqueCitations: Array<{
    document_title: string;
    article: string;
    clause?: string;
    point?: string;
  }> = [];

  sources.forEach((src) => {
    const doc = src.document_title || 'Văn bản';
    const art = src.article_title || (src.article_number ? `Điều ${src.article_number}` : 'N/A');
    const clause = src.clause_number ? `Khoản ${src.clause_number}` : '';
    const point = src.point ? `Điểm ${src.point}` : '';

    const key = `${doc}-${art}-${clause}-${point}`;
    if (!seenCitations.has(key)) {
      seenCitations.add(key);
      uniqueCitations.push({
        document_title: doc,
        article: art,
        clause,
        point,
      });
    }
  });

  return (
    <div className="citations-container">
      <div className="citations-title">Căn Cứ Pháp Lý Được Áp Dụng</div>
      <div className="citation-list">
        {uniqueCitations.map((cit, idx) => (
          <div key={idx} className="citation-row">
            <span className="citation-pill doc">{cit.document_title}</span>
            <span className="citation-pill article">{cit.article}</span>
            {cit.clause && <span className="citation-pill detail">{cit.clause}</span>}
            {cit.point && <span className="citation-pill detail">{cit.point}</span>}
          </div>
        ))}
      </div>
    </div>
  );
};
