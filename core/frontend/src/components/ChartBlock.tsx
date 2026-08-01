import { useEffect, useRef } from "react";

interface ChartBlockProps {
  kind: "echarts" | "mermaid";
  spec: Record<string, unknown> | string;
}

export type { ChartBlockProps };

declare global {
  interface Window {
    echarts?: {
      init: (el: HTMLElement) => {
        setOption: (option: unknown) => void;
        resize: () => void;
        dispose: () => void;
      };
    };
    mermaid?: {
      initialize: (config: Record<string, unknown>) => void;
      render: (id: string, text: string) => Promise<{ svg: string }>;
    };
  }
}

function loadScript(src: string, id: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (document.getElementById(id)) {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.id = id;
    script.src = src;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`Failed to load ${src}`));
    document.head.appendChild(script);
  });
}

export default function ChartBlock({ kind, spec }: ChartBlockProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const chartContainer: HTMLDivElement = container;

    let disposed = false;
    let chart: {
      setOption: (option: unknown) => void;
      resize: () => void;
      dispose: () => void;
    } | null = null;

    async function renderChart() {
      if (kind === "echarts") {
        await loadScript(
          "https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js",
          "engine-echarts",
        );
        if (disposed || !window.echarts) return;
        chart = window.echarts.init(chartContainer);
        chart.setOption(typeof spec === "string" ? JSON.parse(spec) : spec);
        return;
      }

      await loadScript(
        "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js",
        "engine-mermaid",
      );
      if (disposed || !window.mermaid) return;
      window.mermaid.initialize({ startOnLoad: false, theme: "dark" });
      const text = typeof spec === "string" ? spec : String(spec.diagram || "");
      const { svg } = await window.mermaid.render(`mmd-${Date.now()}`, text);
      if (!disposed) chartContainer.innerHTML = svg;
    }

    renderChart().catch(() => {
      if (!disposed) {
        chartContainer.textContent = "Unable to render chart.";
      }
    });

    const onResize = () => chart?.resize();
    window.addEventListener("resize", onResize);
    return () => {
      disposed = true;
      window.removeEventListener("resize", onResize);
      chart?.dispose();
    };
  }, [kind, spec]);

  return <div className="chart-block" ref={containerRef} />;
}

export function parseChartPayload(text: string): ChartBlockProps | null {
  const trimmed = text.trim();
  if (!trimmed.startsWith("{")) return null;
  try {
    const data = JSON.parse(trimmed) as {
      chart_type?: string;
      spec?: Record<string, unknown> | string;
      diagram?: string;
    };
    if (data.chart_type === "echarts" && data.spec) {
      return { kind: "echarts", spec: data.spec };
    }
    if (data.chart_type === "mermaid") {
      return { kind: "mermaid", spec: data.spec || data.diagram || "" };
    }
  } catch {
    return null;
  }
  return null;
}
