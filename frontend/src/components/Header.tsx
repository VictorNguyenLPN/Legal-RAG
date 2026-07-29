import React from 'react';

export const Header: React.FC = () => {
  return (
    <div className="legal-header">
      <div className="legal-header-tag">JurisSearch &bull; AI Legal Assistant</div>
      <h1 className="legal-header-title">Trợ Lý Hỏi Đáp Pháp Luật</h1>
      <div className="legal-header-divider"></div>
      <p className="legal-header-subtitle">
        Hệ thống tra cứu thông minh <br />
        sử dụng mô hình Gemini 2.5 Flash kết hợp tìm kiếm ngữ nghĩa và từ khóa.
      </p>
    </div>
  );
};
