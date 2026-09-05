import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorAlertProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export const ErrorAlert: React.FC<ErrorAlertProps> = ({
  title = 'Service Unavailable',
  message,
  onRetry,
}) => {
  return (
    <div
      style={{
        background: 'rgba(244, 63, 94, 0.08)',
        border: '1px solid rgba(244, 63, 94, 0.25)',
        borderRadius: 'var(--radius-md)',
        padding: '1.25rem',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '0.85rem',
        margin: '1rem 0',
      }}
    >
      <AlertCircle size={20} color="var(--accent-rose)" style={{ flexShrink: 0, marginTop: '2px' }} />
      <div style={{ flex: 1 }}>
        <h4 style={{ fontSize: '0.9rem', color: 'var(--accent-rose)', marginBottom: '0.2rem', fontWeight: 600 }}>
          {title}
        </h4>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
          {message}
        </p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="btn-secondary"
            style={{
              marginTop: '0.75rem',
              padding: '0.35rem 0.75rem',
              fontSize: '0.75rem',
              color: 'var(--accent-rose)',
              borderColor: 'rgba(244, 63, 94, 0.3)',
            }}
          >
            <RefreshCw size={12} />
            <span>Try Again</span>
          </button>
        )}
      </div>
    </div>
  );
};
