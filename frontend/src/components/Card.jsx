/**
 * Card Component
 * Reusable card container
 */

const Card = ({ children, className = '', padding = 'md', hover = false }) => {
  const paddingSizes = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  };

  const hoverClass = hover ? 'hover:shadow-lg transition-shadow cursor-pointer' : '';

  return (
    <div className={`bg-white rounded-lg shadow ${paddingSizes[padding]} ${hoverClass} ${className}`}>
      {children}
    </div>
  );
};

export default Card;
