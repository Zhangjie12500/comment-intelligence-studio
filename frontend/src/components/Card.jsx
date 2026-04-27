export default function Card({ children, className = '', ...rest }) {
  return (
    <div
      className={`rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className = '' }) {
  return (
    <div className={`px-4 pt-4 pb-3 border-b border-white/8 ${className}`}>
      {children}
    </div>
  );
}

export function CardBody({ children, className = '' }) {
  return <div className={`p-4 ${className}`}>{children}</div>;
}
