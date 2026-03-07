'use client';

import { useEffect, useRef, useState } from 'react';

interface Props {
  chart: string;
  className?: string;
}

export default function MermaidChart({ chart, className }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ref.current || !chart.trim()) return;

    let cancelled = false;

    (async () => {
      try {
        const mermaid = (await import('mermaid')).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: 'base',
          themeVariables: {
            primaryColor:      '#3b82f6',
            primaryTextColor:  '#fff',
            primaryBorderColor:'#2563eb',
            lineColor:         '#64748b',
            secondaryColor:    '#f0fdf4',
            tertiaryColor:     '#eff6ff',
            background:        '#1e293b',
            mainBkg:           '#1e293b',
            nodeBorder:        '#3b82f6',
            clusterBkg:        '#0f172a',
            titleColor:        '#e2e8f0',
            edgeLabelBackground: '#1e293b',
            fontFamily: 'Pretendard, system-ui, sans-serif',
          },
          securityLevel: 'loose',
        });

        const id = `mermaid-${Math.random().toString(36).slice(2)}`;
        const { svg } = await mermaid.render(id, chart);

        if (!cancelled && ref.current) {
          ref.current.innerHTML = svg;
          // SVG 크기 조정
          const svgEl = ref.current.querySelector('svg');
          if (svgEl) {
            svgEl.style.width = '100%';
            svgEl.style.height = 'auto';
            svgEl.style.maxHeight = '280px';
          }
          setError(null);
        }
      } catch (e: unknown) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Mermaid 렌더링 오류');
        }
      }
    })();

    return () => { cancelled = true; };
  }, [chart]);

  if (error) {
    return (
      <div style={{
        padding: '10px 14px',
        background: '#1e293b',
        color: '#94a3b8',
        fontSize: '0.72rem',
        fontFamily: 'monospace',
        borderRadius: '6px',
        whiteSpace: 'pre-wrap',
        overflowX: 'auto',
      }}>
        {/* 오류 시 raw 텍스트로 폴백 */}
        {chart}
      </div>
    );
  }

  return (
    <div
      ref={ref}
      className={className}
      style={{
        background: '#1e293b',
        borderRadius: '6px',
        padding: '12px',
        overflowX: 'auto',
        minHeight: '60px',
      }}
    />
  );
}
