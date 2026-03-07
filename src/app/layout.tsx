import type { Metadata } from 'next';
import '../styles/globals.css';

export const metadata: Metadata = {
  title: 'CheckPoint | 소상공인 경영 인사이트',
  description: '매출 분석부터 지원사업 매칭까지, 사장님을 위한 경영 비서',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
