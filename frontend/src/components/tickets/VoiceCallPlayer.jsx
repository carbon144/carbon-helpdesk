import { useState } from 'react';

export default function VoiceCallPlayer({ voiceCall }) {
  const [showTranscript, setShowTranscript] = useState(false);

  if (!voiceCall) return null;

  const duration = voiceCall.duration_seconds
    ? `${Math.floor(voiceCall.duration_seconds / 60)}:${String(Math.floor(voiceCall.duration_seconds % 60)).padStart(2, '0')}`
    : '--:--';

  return (
    <div style={{
      border: '1px solid #e2e8f0',
      borderRadius: '8px',
      padding: '12px',
      marginBottom: '12px',
      backgroundColor: '#f8fafc',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
        <span style={{ fontSize: '18px' }}>📞</span>
        <strong>Ligacao telefonica</strong>
        <span style={{ color: '#64748b', fontSize: '13px' }}>
          {duration} · {new Date(voiceCall.created_at).toLocaleString('pt-BR')}
        </span>
      </div>

      {voiceCall.recording_url && (
        <audio controls style={{ width: '100%', marginBottom: '8px' }}>
          <source src={voiceCall.recording_url} />
        </audio>
      )}

      {voiceCall.summary && (
        <p style={{ margin: '4px 0 8px', color: '#475569', fontSize: '14px' }}>
          <strong>Resumo:</strong> {voiceCall.summary}
        </p>
      )}

      {voiceCall.transcript && (
        <>
          <button
            onClick={() => setShowTranscript(!showTranscript)}
            style={{
              background: 'none',
              border: '1px solid #cbd5e1',
              borderRadius: '4px',
              padding: '4px 12px',
              cursor: 'pointer',
              fontSize: '13px',
              color: '#475569',
            }}
          >
            {showTranscript ? 'Ocultar transcricao' : 'Ver transcricao'}
          </button>
          {showTranscript && (
            <pre style={{
              marginTop: '8px',
              padding: '10px',
              backgroundColor: '#fff',
              border: '1px solid #e2e8f0',
              borderRadius: '4px',
              fontSize: '13px',
              whiteSpace: 'pre-wrap',
              maxHeight: '300px',
              overflow: 'auto',
            }}>
              {voiceCall.transcript}
            </pre>
          )}
        </>
      )}
    </div>
  );
}
