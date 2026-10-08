import React, { useEffect, useRef } from 'react';

const AgentTerminal = ({ logs = [], systemState }) => {
  const terminalRef = useRef(null);

  useEffect(() => {
    if (terminalRef.current) terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
  }, [logs]);

  return (
    <div className="agent-terminal" ref={terminalRef}>
      {!logs.length ? <div className="agent-terminal-empty">Monitoring is active. Agent actions will appear here.</div> : logs.map((log, index) => (
        <div key={`${log.request_id || log.time}-${index}`} className="agent-log">
          <span className="log-timestamp">{log.timestamp}</span>
          <span className="log-service">{log.service || 'AutoSRE'}</span>
          <span className={`log-level log-level-${(log.level || 'INFO').toLowerCase()}`}>{log.level || log.type || 'INFO'}</span>
          <span className={`agent-name`}>{log.agent}</span>
          <span className="agent-message" title={`Request: ${log.request_id || '—'} · Trace: ${log.trace_id || '—'} · Incident: ${log.incident_id || '—'}`}>{log.message}</span>
        </div>
      ))}
      {systemState === 'recovering' && <div className="agent-terminal-empty">Post-recovery verification in progress…</div>}
    </div>
  );
};

export default AgentTerminal;
