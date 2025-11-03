/**
 * Embedding Statistics Chart
 * Histogram showing the distribution of embedding values
 */

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const EmbeddingStatsChart = ({ embedding }) => {
  if (!embedding || embedding.length === 0) {
    return (
      <div className="text-gray-500 text-sm p-4 bg-gray-50 rounded">
        No embedding data available
      </div>
    );
  }

  // Calculate statistics
  const min = Math.min(...embedding);
  const max = Math.max(...embedding);
  const mean = embedding.reduce((a, b) => a + b, 0) / embedding.length;
  const variance = embedding.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / embedding.length;
  const stdDev = Math.sqrt(variance);

  // Create histogram bins
  const numBins = 20;
  const binSize = (max - min) / numBins;
  const bins = Array(numBins).fill(0).map((_, i) => ({
    range: `${(min + i * binSize).toFixed(2)}`,
    count: 0,
    binIndex: i,
    rangeStart: min + i * binSize,
    rangeEnd: min + (i + 1) * binSize
  }));

  // Fill bins
  embedding.forEach(value => {
    const binIndex = Math.min(Math.floor((value - min) / binSize), numBins - 1);
    bins[binIndex].count++;
  });

  // Color bins based on position (blue for negative, red for positive)
  const getBinColor = (rangeStart, rangeEnd) => {
    const midpoint = (rangeStart + rangeEnd) / 2;
    if (midpoint < -0.1) return '#3b82f6'; // blue for negative
    if (midpoint > 0.1) return '#ef4444'; // red for positive
    return '#6b7280'; // gray for near-zero
  };

  return (
    <div className="space-y-4">
      {/* Statistics Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-gray-600 mb-1">Minimum</p>
          <p className="text-lg font-semibold text-gray-900">{min.toFixed(4)}</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-gray-600 mb-1">Maximum</p>
          <p className="text-lg font-semibold text-gray-900">{max.toFixed(4)}</p>
        </div>
        <div className="bg-blue-50 rounded-lg p-3">
          <p className="text-blue-700 mb-1">Mean (μ)</p>
          <p className="text-lg font-semibold text-blue-900">{mean.toFixed(4)}</p>
        </div>
        <div className="bg-blue-50 rounded-lg p-3">
          <p className="text-blue-700 mb-1">Std Dev (σ)</p>
          <p className="text-lg font-semibold text-blue-900">{stdDev.toFixed(4)}</p>
        </div>
      </div>

      {/* Distribution Chart */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-900 mb-3">Value Distribution</h4>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={bins} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="range"
              tick={{ fontSize: 10 }}
              angle={-45}
              textAnchor="end"
              height={60}
              stroke="#6b7280"
            />
            <YAxis
              tick={{ fontSize: 12 }}
              stroke="#6b7280"
              label={{ value: 'Frequency', angle: -90, position: 'insideLeft', style: { fontSize: 12 } }}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  return (
                    <div className="bg-gray-900 text-white text-xs px-3 py-2 rounded shadow-lg">
                      <p className="font-medium">Range: {data.rangeStart.toFixed(3)} to {data.rangeEnd.toFixed(3)}</p>
                      <p>Count: {data.count} dimensions</p>
                      <p className="text-gray-300">
                        {((data.count / embedding.length) * 100).toFixed(1)}% of total
                      </p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {bins.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getBinColor(entry.rangeStart, entry.rangeEnd)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <p className="text-xs text-gray-500 mt-2 text-center">
          Distribution of {embedding.length} embedding dimensions across {numBins} bins
        </p>
      </div>

      {/* Interpretation */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-xs text-yellow-900">
        <p className="font-medium mb-1">💡 Interpretation</p>
        <p>
          The distribution shows how embedding values are spread across dimensions.
          A normal (bell-curve) distribution suggests balanced feature representation.
          Skewed distributions may indicate specialized or domain-specific content.
        </p>
      </div>
    </div>
  );
};

export default EmbeddingStatsChart;
