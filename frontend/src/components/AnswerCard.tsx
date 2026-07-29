import React from 'react';

interface AnswerCardProps {
  answer: string;
}

export const AnswerCard: React.FC<AnswerCardProps> = ({ answer }) => {
  return (
    <div className="legal-opinion-card">
      <div className="legal-opinion-title">Phân Tích Pháp Lý Sơ Bộ</div>
      <div className="legal-opinion-text">{answer}</div>
    </div>
  );
};
