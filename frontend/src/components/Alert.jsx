/**
 * Alert Component
 * Display messages and notifications
 */

const Alert = ({ type = 'info', message, onClose, className = '' }) => {
  const types = {
    info: 'bg-blue-50 border-blue-500 text-blue-900',
    success: 'bg-green-50 border-green-500 text-green-900',
    warning: 'bg-yellow-50 border-yellow-500 text-yellow-900',
    error: 'bg-red-50 border-red-500 text-red-900',
  };

  const icons = {
    info: '💡',
    success: '✓',
    warning: '⚠',
    error: '✕',
  };

  if (!message) return null;

  return (
    <div className={`border-l-4 p-4 ${types[type]} ${className} flex items-start justify-between`}>
      <div className="flex items-start gap-3">
        <span className="text-xl">{icons[type]}</span>
        <p className="text-sm">{message}</p>
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-gray-700 text-xl leading-none"
        >
          ×
        </button>
      )}
    </div>
  );
};

export default Alert;
