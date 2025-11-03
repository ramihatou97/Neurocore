/**
 * Embedding Heatmap Visualization
 * Visual representation of embedding vector with color-coded cells
 */

import { useState } from 'react';

const EmbeddingHeatmap = ({ embedding, dimensions = 1536 }) => {
  const [hoveredCell, setHoveredCell] = useState(null);

  if (!embedding || embedding.length === 0) {
    return (
      <div className="text-gray-500 text-sm p-4 bg-gray-50 rounded">
        No embedding data available
      </div>
    );
  }

  // Calculate grid dimensions for optimal layout
  const cellsPerRow = 64; // 64 columns = 24 rows for 1536 dimensions
  const totalRows = Math.ceil(embedding.length / cellsPerRow);
  const cellSize = 12; // pixels

  // Get color for value (blue=negative, white=0, red=positive)
  const getColor = (value) => {
    // Normalize to 0-1 range (embeddings typically range from -1 to 1)
    const normalized = (value + 1) / 2;
    const clamped = Math.max(0, Math.min(1, normalized));

    if (value < 0) {
      // Blue gradient for negative values
      const intensity = Math.floor((1 - clamped * 2) * 255);
      return `rgb(${intensity}, ${intensity}, 255)`;
    } else {
      // Red gradient for positive values
      const intensity = Math.floor((clamped * 2 - 1) * 255);
      return `rgb(255, ${255 - intensity}, ${255 - intensity})`;
    }
  };

  // Get all values for statistics
  const min = Math.min(...embedding);
  const max = Math.max(...embedding);
  const mean = embedding.reduce((a, b) => a + b, 0) / embedding.length;

  return (
    <div className="space-y-4">
      {/* Legend */}
      <div className="flex items-center justify-between text-xs text-gray-600">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-blue-500 rounded"></div>
            <span>Negative ({min.toFixed(3)})</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-white border border-gray-300 rounded"></div>
            <span>Zero</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-red-500 rounded"></div>
            <span>Positive ({max.toFixed(3)})</span>
          </div>
        </div>
        <div>
          <span className="font-medium">Mean:</span> {mean.toFixed(6)}
        </div>
      </div>

      {/* Heatmap Grid */}
      <div className="relative bg-white border border-gray-200 rounded-lg p-4 overflow-auto">
        <div
          className="relative"
          style={{
            width: cellsPerRow * cellSize,
            height: totalRows * cellSize
          }}
        >
          {embedding.map((value, index) => {
            const row = Math.floor(index / cellsPerRow);
            const col = index % cellsPerRow;

            return (
              <div
                key={index}
                className="absolute cursor-pointer transition-transform hover:scale-150 hover:z-10 border border-gray-100"
                style={{
                  left: col * cellSize,
                  top: row * cellSize,
                  width: cellSize,
                  height: cellSize,
                  backgroundColor: getColor(value),
                }}
                onMouseEnter={() => setHoveredCell({ index, value })}
                onMouseLeave={() => setHoveredCell(null)}
                title={`[${index}]: ${value.toFixed(6)}`}
              />
            );
          })}
        </div>

        {/* Hover Tooltip */}
        {hoveredCell && (
          <div className="absolute top-2 right-2 bg-gray-900 text-white text-xs px-3 py-2 rounded shadow-lg z-20">
            <div className="font-mono">
              <div><span className="text-gray-400">Index:</span> {hoveredCell.index}</div>
              <div><span className="text-gray-400">Value:</span> {hoveredCell.value.toFixed(6)}</div>
            </div>
          </div>
        )}
      </div>

      {/* Grid Info */}
      <div className="text-xs text-gray-500 text-center">
        {embedding.length} dimensions • {cellsPerRow} columns × {totalRows} rows
      </div>
    </div>
  );
};

export default EmbeddingHeatmap;
