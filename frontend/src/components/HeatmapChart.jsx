import { useState, useRef, useEffect } from 'react';
import { AlertCircle } from 'lucide-react';

const SENTIMENT_COLORS = {
  positive: { bg: '#DBEAFE', border: '#93C5FD', text: '#1E40AF' },
  neutral: { bg: '#F3F4F6', border: '#D1D5DB', text: '#374151' },
  negative: { bg: '#FEE2E2', border: '#FCA5A5', text: '#991B1B' },
  mixed: { bg: '#FEF3C7', border: '#FCD34D', text: '#92400E' },
};

const SENTIMENT_LABELS = {
  positive: '正面',
  neutral: '中性',
  negative: '负面',
  mixed: '混合',
};

export default function HeatmapChart({ heatmapData }) {
  const [hoveredCell, setHoveredCell] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);

  // Handle missing or invalid data
  if (!heatmapData || !heatmapData.values || heatmapData.values.length === 0) {
    return (
      <div className="p-6 rounded-lg text-center">
        <div className="w-14 h-14 rounded-xl flex items-center justify-center mx-auto mb-4"
          style={{ background: '#F3F4F6', border: '1px dashed #D1D5DB' }}>
          <AlertCircle size={24} className="text-[#9CA3AF]" />
        </div>
        <h4 className="text-sm font-semibold text-[#374151] mb-2">暂不生成热力图</h4>
        <p className="text-xs text-[#6B7280] mb-4">
          当前视频未检测到足够的商品或评价维度，无法生成"商品 × 维度"对比热力图。
        </p>
        <p className="text-xs" style={{ color: '#B45309', background: '#FEF3C7', padding: '8px', borderRadius: '6px' }}>
          建议：可尝试提高评论抓取数量，或使用多商品测评类视频进行分析。
        </p>
      </div>
    );
  }

  const { x_axis = [], y_axis = [], unit = '评论倾向值', value_explanation = '', values = [] } = heatmapData;

  // Build value map for quick lookup
  const valueMap = {};
  values.forEach(v => {
    valueMap[`${v.product}-${v.aspect}`] = v;
  });

  // Get heat color based on value (0-100)
  const getHeatColor = (value) => {
    // Blue gradient from light to dark based on value
    const intensity = value / 100;
    // Light blue (low) to dark blue (high)
    const r = Math.round(239 - intensity * 180); // 239 -> 59
    const g = Math.round(246 - intensity * 160); // 246 -> 86
    const b = Math.round(254 - intensity * 80);  // 254 -> 174
    return `rgb(${r}, ${g}, ${b})`;
  };

  const handleMouseEnter = (e, product, aspect, value) => {
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left + 10;
    const y = e.clientY - rect.top - 10;
    setTooltipPos({ x, y });
    setHoveredCell({ product, aspect, value });
  };

  const handleMouseLeave = () => {
    setHoveredCell(null);
  };

  const handleMouseMove = (e) => {
    if (hoveredCell && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      setTooltipPos({
        x: e.clientX - rect.left + 15,
        y: e.clientY - rect.top - 15,
      });
    }
  };

  // Find hovered cell data
  const hoveredCellData = hoveredCell
    ? valueMap[`${hoveredCell.product}-${hoveredCell.aspect}`]
    : null;

  return (
    <div className="p-5">
      {/* Heatmap container */}
      <div ref={containerRef} className="relative" onMouseMove={handleMouseMove}>
        {/* Header row */}
        <div className="flex mb-1">
          {/* Empty corner cell */}
          <div className="w-20 flex-shrink-0" />

          {/* X-axis labels */}
          {x_axis.map((label, i) => (
            <div
              key={i}
              className="flex-1 text-center text-xs font-medium px-1 py-2"
              style={{ color: '#374151' }}
            >
              {label}
            </div>
          ))}
        </div>

        {/* Data rows */}
        {y_axis.map((product, rowIdx) => (
          <div key={rowIdx} className="flex mb-1">
            {/* Y-axis label */}
            <div
              className="w-20 flex-shrink-0 text-xs font-medium px-2 py-3 flex items-center"
              style={{ color: '#374151' }}
            >
              {product}
            </div>

            {/* Heat cells */}
            {x_axis.map((aspect, colIdx) => {
              const cellData = valueMap[`${product}-${aspect}`];
              const value = cellData?.value || 0;
              const sentiment = cellData?.sentiment || 'neutral';
              const count = cellData?.count || 0;
              const isHovered = hoveredCell?.product === product && hoveredCell?.aspect === aspect;

              return (
                <div
                  key={colIdx}
                  className="flex-1 aspect-square flex items-center justify-center cursor-pointer transition-all duration-150 rounded"
                  style={{
                    background: getHeatColor(value),
                    border: isHovered ? '2px solid #2563EB' : '1px solid transparent',
                    transform: isHovered ? 'scale(1.05)' : 'scale(1)',
                    boxShadow: isHovered ? '0 4px 12px rgba(37,99,235,0.3)' : 'none',
                  }}
                  onMouseEnter={(e) => handleMouseEnter(e, product, aspect, value)}
                  onMouseLeave={handleMouseLeave}
                >
                  {count > 0 ? (
                    <span
                      className="text-xs font-semibold"
                      style={{ color: value > 50 ? '#1E40AF' : '#374151' }}
                    >
                      {Math.round(value)}
                    </span>
                  ) : (
                    <span className="text-xs" style={{ color: '#9CA3AF' }}>
                      -
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        ))}

        {/* Tooltip */}
        {hoveredCell && hoveredCellData && (
          <div
            className="absolute z-50 p-3 rounded-lg shadow-lg text-xs min-w-[180px] pointer-events-none"
            style={{
              left: `${tooltipPos.x}px`,
              top: `${tooltipPos.y}px`,
              background: '#FFFFFF',
              border: '1px solid #E5E7EB',
              boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
            }}
          >
            <div className="font-semibold text-[#111827] mb-2">
              {hoveredCell.product} × {hoveredCell.aspect}
            </div>
            <div className="space-y-1.5">
              <div className="flex justify-between">
                <span style={{ color: '#6B7280' }}>数值：</span>
                <span className="font-semibold" style={{ color: '#111827' }}>
                  {hoveredCell.value.toFixed(1)}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span style={{ color: '#6B7280' }}>情绪：</span>
                <span
                  className="px-2 py-0.5 rounded text-xs font-medium"
                  style={{
                    background: SENTIMENT_COLORS[hoveredCellData.sentiment]?.bg || SENTIMENT_COLORS.neutral.bg,
                    color: SENTIMENT_COLORS[hoveredCellData.sentiment]?.text || SENTIMENT_COLORS.neutral.text,
                  }}
                >
                  {SENTIMENT_LABELS[hoveredCellData.sentiment] || '中性'}
                </span>
              </div>
              <div className="flex justify-between">
                <span style={{ color: '#6B7280' }}>评论数：</span>
                <span style={{ color: '#111827' }}>{hoveredCellData.count || 0}</span>
              </div>
              {hoveredCellData.examples && hoveredCellData.examples.length > 0 && (
                <div className="pt-1 border-t border-[#E5E7EB] mt-1">
                  <div style={{ color: '#6B7280' }} className="mb-1">代表评论：</div>
                  {hoveredCellData.examples.slice(0, 2).map((ex, i) => (
                    <div
                      key={i}
                      className="text-xs italic truncate mb-1"
                      style={{ color: '#4B5563' }}
                    >
                      "{ex}"
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="mt-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span className="text-xs text-[#6B7280]">低</span>
          <div className="flex">
            {[0, 25, 50, 75, 100].map((val) => (
              <div
                key={val}
                className="w-8 h-4 first:rounded-l last:rounded-r"
                style={{ background: getHeatColor(val) }}
              />
            ))}
          </div>
          <span className="text-xs text-[#6B7280]">高</span>
        </div>
        <div className="flex items-center gap-3">
          {Object.entries(SENTIMENT_LABELS).map(([key, label]) => (
            <div key={key} className="flex items-center gap-1">
              <span
                className="w-3 h-3 rounded"
                style={{
                  background: SENTIMENT_COLORS[key]?.bg || '#F3F4F6',
                  border: `1px solid ${SENTIMENT_COLORS[key]?.border || '#D1D5DB'}`,
                }}
              />
              <span className="text-xs" style={{ color: '#6B7280' }}>{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Unit and explanation */}
      <div className="mt-4 pt-3 border-t border-[#F3F4F6]">
        <p className="text-xs text-[#6B7280]">
          <span className="font-medium">单位：</span>{unit}
        </p>
        {value_explanation && (
          <p className="text-xs text-[#9CA3AF] mt-1 italic">{value_explanation}</p>
        )}
      </div>
    </div>
  );
}
