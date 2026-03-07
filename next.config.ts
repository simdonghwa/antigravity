import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Docker 배포 시 standalone 모드 (Vercel은 자동 감지하여 무시)
  output: process.env.DOCKER_BUILD ? "standalone" : undefined,

  // 프로덕션 보안/최적화
  compress: true,
  poweredByHeader: false,

  // Mermaid는 클라이언트 전용 라이브러리 — 서버 번들 제외 (Next.js 16 Turbopack 호환)
  serverExternalPackages: ["mermaid"],
};

export default nextConfig;
