/**
 * ProgressBar Component
 * Displays progress with percentage
 */

const ProgressBar = ({ progress, showPercentage = true, size = 'md', className = '' }) => {
  const sizeClasses = {
    sm: 'h-2',
    md: 'h-4',
    lg: 'h-6',
  };

  const safeProgress = Math.min(Math.max(progress, 0), 100);

  return (
    <div className={className}>
      <div className={`w-full bg-gray-200 rounded-full overflow-hidden ${sizeClasses[size]}`}>
        <div
          className="h-full bg-blue-600 transition-all duration-300 ease-in-out"
          style={{ width: `${safeProgress}%` }}
        />
      </div>
      {showPercentage && (
        <p className="text-sm text-gray-600 mt-1 text-right">{safeProgress}%</p>
      )}
    </div>
  );
};

export default ProgressBar;
