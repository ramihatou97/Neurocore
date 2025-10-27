/**
 * Badge Component
 * Display status badges and tags
 */

import { getStatusColor } from '../utils/helpers';

const Badge = ({ children, status, variant = 'default', className = '' }) => {
  // Use status color if status provided
  const colorClass = status
    ? getStatusColor(status)
    : variant === 'default'
    ? 'text-gray-700 bg-gray-100'
    : variant === 'primary'
    ? 'text-blue-700 bg-blue-100'
    : variant === 'success'
    ? 'text-green-700 bg-green-100'
    : variant === 'warning'
    ? 'text-yellow-700 bg-yellow-100'
    : variant === 'danger'
    ? 'text-red-700 bg-red-100'
    : 'text-gray-700 bg-gray-100';

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClass} ${className}`}>
      {children}
    </span>
  );
};

export default Badge;
