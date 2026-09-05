import React, { useState } from 'react';
import { askCopilot } from '../api/client';
import { CopilotResponse } from '../api/types';
import { EvidencePanel } from '../components/EvidencePanel';
import { ErrorAlert } from '../components/ErrorAlert';
import { 
  Sparkles, 
  Send, 
  Bot, 
  User, 
  HelpCircle, 
  AlertTriangle, 
  CheckCircle2, 
  Lightbulb, 
  ArrowRightCircle, 
  ShieldCheck 
} from 'lucide-react';

interface ChatMessage {
  id: string;
  sender: 'user' | 'copilot';
  text: string;
  response?: CopilotResponse;
  isLoading?: boolean;
}

export const CopilotPage: React.FC = () => {
  const [question, setQuestion] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome-1',
      sender: 'copilot',
      text: 'Hello! I am your RetailIQ Evidence-First Copilot. Ask me any business question about inventory risk, replenishment quantities, sales velocity, top stores, or revenue trends. Every answer is grounded directly in verified SQLite transactions.',
    },
  ]);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const suggestedQuestions = [
    'Which products are likely to run out soon?',
    'Which store generated the most revenue?',
    'How did the wireless mouse perform this month?',
    'What products are overstocked?',
    'Why should I reorder the USB-C cable?',
    'What should I pay attention to today?',
  ];

  const handleSend = async (queryText?: string) => {
    const q = (queryText || question).trim();
    if (!q || isSubmitting) return;

    setError(null);
    setQuestion('');

    const userMsgId = `user-${Date.now()}`;
    const botMsgId = `copilot-${Date.now()}`;

    // Add user message & loading copilot placeholder
    setMessages((prev) => [
      ...prev,
      { id: userMsgId, sender: 'user', text: q },
      { id: botMsgId, sender: 'copilot', text: '', isLoading: true },
    ]);

    setIsSubmitting(true);

    try {
      const response = await askCopilot(q);

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === botMsgId
            ? {
                ...msg,
                text: response.answer,
                response,
                isLoading: false,
              }
            : msg
        )
      );
    } catch (err: any) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === botMsgId
            ? {
                ...msg,
                text: 'An error occurred while connecting to the Retail Copilot. Please check your connection and try again.',
                isLoading: false,
              }
            : msg
        )
      );
      setError(err.message || 'Copilot query failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="page-container" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 85px)', paddingBottom: '1rem' }}>
      {/* Title */}
      <div style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Sparkles size={22} color="var(--accent-purple)" />
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800 }}>RetailIQ Copilot</h2>
        </div>
        <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>
          Ask questions about sales, inventory, products, stores, trends, and recommended actions.
        </p>
      </div>

      {error && <ErrorAlert message={error} />}

      {/* Suggested Prompt Chips */}
      <div style={{ display: 'flex', gap: '0.4rem', overflowX: 'auto', paddingBottom: '0.65rem', marginBottom: '0.75rem' }}>
        {suggestedQuestions.map((sq, i) => (
          <button
            key={i}
            onClick={() => handleSend(sq)}
            disabled={isSubmitting}
            className="chip"
            style={{ fontSize: '0.75rem', padding: '0.35rem 0.75rem' }}
          >
            {sq}
          </button>
        ))}
      </div>

      {/* Messages Scroll Area */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          background: 'rgba(11, 15, 25, 0.65)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-md)',
          padding: '1.25rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1.25rem',
          marginBottom: '1rem',
        }}
      >
        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              display: 'flex',
              gap: '0.85rem',
              maxWidth: msg.sender === 'user' ? '80%' : '100%',
              alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start',
            }}
          >
            {/* Avatar */}
            <div
              style={{
                width: '34px',
                height: '34px',
                borderRadius: '8px',
                background:
                  msg.sender === 'user'
                    ? 'rgba(56, 189, 248, 0.15)'
                    : 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
                color: msg.sender === 'user' ? 'var(--accent-blue)' : '#fff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                border: msg.sender === 'user' ? '1px solid rgba(56, 189, 248, 0.3)' : 'none',
              }}
            >
              {msg.sender === 'user' ? <User size={18} /> : <Bot size={18} />}
            </div>

            {/* Bubble */}
            <div
              style={{
                background: msg.sender === 'user' ? 'rgba(30, 41, 59, 0.75)' : 'var(--bg-card)',
                border: `1px solid ${msg.sender === 'user' ? '#334155' : 'var(--border-color)'}`,
                borderRadius: 'var(--radius-md)',
                padding: '1rem 1.15rem',
                fontSize: '0.875rem',
                color: 'var(--text-primary)',
                boxShadow: 'var(--shadow-card)',
                width: msg.sender === 'copilot' ? '100%' : 'auto',
              }}
            >
              {msg.isLoading ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', color: 'var(--text-muted)' }}>
                  <Sparkles size={16} className="animate-spin" color="var(--accent-purple)" />
                  <span style={{ fontSize: '0.825rem' }}>Analyzing query against deterministic SQLite engine...</span>
                </div>
              ) : (
                <>
                  {/* Ambiguity Card */}
                  {msg.response?.needs_clarification ? (
                    <div style={{ background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.25)', borderRadius: 'var(--radius-sm)', padding: '0.85rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--accent-amber)', fontWeight: 700, fontSize: '0.85rem', marginBottom: '0.35rem' }}>
                        <HelpCircle size={16} />
                        <span>I need a little more information</span>
                      </div>
                      <p style={{ fontSize: '0.85rem', color: 'var(--text-primary)', marginBottom: '0.75rem' }}>
                        {msg.response.clarification_question || msg.text}
                      </p>
                    </div>
                  ) : (
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                        <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--accent-purple)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          Copilot Synthesis
                        </div>
                        {msg.response?.intent && (
                          <span className="badge badge-purple" style={{ fontSize: '0.65rem' }}>
                            {msg.response.intent}
                          </span>
                        )}
                      </div>
                      <p style={{ lineHeight: 1.55, fontSize: '0.9rem' }}>{msg.text}</p>
                    </div>
                  )}

                  {/* Partial Data Notice */}
                  {msg.response?.data_status === 'incomplete' && (
                    <div
                      style={{
                        margin: '0.75rem 0',
                        padding: '0.5rem 0.75rem',
                        background: 'rgba(245, 158, 11, 0.08)',
                        border: '1px solid rgba(245, 158, 11, 0.25)',
                        borderRadius: 'var(--radius-sm)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        fontSize: '0.775rem',
                        color: 'var(--accent-amber)',
                      }}
                    >
                      <AlertTriangle size={15} />
                      <span>Limited data available: The requested time window extends beyond verified dataset dates.</span>
                    </div>
                  )}

                  {/* Structured Recommendations */}
                  {msg.response?.recommendations && msg.response.recommendations.length > 0 && (
                    <div style={{ marginTop: '0.85rem', background: 'rgba(56, 189, 248, 0.06)', border: '1px solid rgba(56, 189, 248, 0.2)', borderRadius: 'var(--radius-sm)', padding: '0.75rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--accent-blue)', fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase', marginBottom: '0.4rem' }}>
                        <Lightbulb size={14} />
                        <span>Actionable Recommendations</span>
                      </div>
                      <ul style={{ paddingLeft: '1.2rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                        {msg.response.recommendations.map((rec, i) => (
                          <li key={i} style={{ marginBottom: '0.25rem' }}>{rec}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Grounded Evidence Box */}
                  {msg.response?.evidence && msg.response.evidence.length > 0 && (
                    <EvidencePanel
                      evidence={msg.response.evidence}
                      assumptions={msg.response.assumptions}
                      dataStatus={msg.response.data_status}
                    />
                  )}
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Input Box */}
      <div
        style={{
          display: 'flex',
          gap: '0.5rem',
          background: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-md)',
          padding: '0.5rem 0.75rem',
          alignItems: 'center',
        }}
      >
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about sales velocity, inventory risks, or replenishment..."
          disabled={isSubmitting}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: 'var(--text-primary)',
            fontSize: '0.875rem',
            fontFamily: 'var(--font-sans)',
            padding: '0.4rem 0.5rem',
          }}
        />
        <button
          onClick={() => handleSend()}
          disabled={isSubmitting || !question.trim()}
          className="btn-primary"
          style={{ padding: '0.5rem 1.15rem' }}
        >
          <Send size={15} />
          <span>Ask</span>
        </button>
      </div>
    </div>
  );
};
