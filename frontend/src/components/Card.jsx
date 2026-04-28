export default function Card({ children, className = '', style = {}, ...rest }) {
  return (
    <div
      className={`bg-white rounded-xl border border-[#E5E7EB] shadow-sm card-hover ${className}`}
      style={{
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02)',
        ...style,
      }}
      {...rest}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className = '' }) {
  return (
    <div className={`px-5 pt-5 pb-4 border-b border-[#F3F4F6] ${className}`}>
      {children}
    </div>
  );
}

export function CardBody({ children, className = '' }) {
  return <div className={`p-5 ${className}`}>{children}</div>;
}

export function CardTitle({ children, icon: Icon, className = '' }) {
  return (
    <div className="flex items-center gap-2">
      {Icon && <Icon size={15} className="text-[#9CA3AF]" />}
      <span className="text-xs font-semibold text-[#6B7280] tracking-wide uppercase">
        {children}
      </span>
    </div>
  );
}
