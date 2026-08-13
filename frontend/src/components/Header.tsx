import React from 'react';

export const Header: React.FC = () => {
  return (
    <div className="legal-header">
      <div className="legal-header-tag">JurisSearch &bull; AI Legal Assistant</div>
      <h1 className="legal-header-title">Trợ Lý Hỏi Đáp Pháp Luật</h1>
      <div className="legal-header-divider"></div>
      <p className="legal-header-subtitle">
        Hệ thống tra cứu thông minh sử dụng mô hình Gemini 3.1 Flash <br />
        kết hợp tìm kiếm ngữ nghĩa kết hợp từ khóa và tái xếp hạng.
      </p>
    </div>
  );
};
