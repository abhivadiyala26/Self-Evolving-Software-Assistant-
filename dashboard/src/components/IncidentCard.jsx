import React, { useEffect, useState } from 'react';
import SeverityBadge from './SeverityBadge';
import { AlertCircle, CheckCircle, Clock, Server, ArrowRight, ShieldAlert } from 'lucide-react';
import './IncidentManagement.css';

const IncidentCard = ({ incident }) => {
  const [nowEpoch, setNowEpoch] = useState(0);
  const incidentId = incident?.incident_id;
  const startTimestamp = incident?.start_timestamp;
  const totalDuration = incident?.total_duration;
  const incidentFinished = ['resolved', 'remediation_failed'].includes(incident?.status);

  useEffect(() => {
    if (!incidentId || totalDuration || incidentFinished) return undefined;

    const interval = setInterval(() => {
      setNowEpoch(Math.floor(Date.now() / 1000));
    }, 1000);

    return () => clearInterval(interval);
  }, [incidentId, startTimestamp, totalDuration, incidentFinished]);

  if (!incident) {
    return (
      <div className="incident-card-empty">
        <CheckCircle size={30} color="#34745b" />
        <div className="empty-title">All Systems Operational</div>
        <p className="empty-sub">No active incidents detected. Monitoring baseline metrics...</p>
      </div>
    );
  }

  const {
    incident_id,
    scenario,
    severity,
    status,
    affected_services = {},
    root_cause,
    symptoms,
    executed_action,
    start_time,
  } = incident;

  const directSvc = affected_services.directly_affected || [];
  const downstreamSvc = affected_services.downstream_affected || [];
  const elapsed = incident.total_duration || (nowEpoch && incident.start_timestamp ? Math.max(1, nowEpoch - Math.floor(incident.start_timestamp)) : 0);

  const getStatusBadge = (st) => {
    switch (st) {
      case 'investigating':
        return <span className="st-badge st-investigating"><Clock size={12}/> INVESTIGATING</span>;
      case 'rca':
        return <span className="st-badge st-rca"><AlertCircle size={12}/> ROOT CAUSE ANALYSIS</span>;
      case 'remediation':
        return <span className="st-badge st-remediation"><ShieldAlert size={12}/> REMEDIATION IN PROGRESS</span>;
      case 'awaiting_approval':
        return <span className="st-badge st-remediation"><ShieldAlert size={12}/> AWAITING ADMIN APPROVAL</span>;
      case 'recovering':
        return <span className="st-badge st-recovering"><Clock size={12}/> RECOVERING</span>;
      case 'resolved':
        return <span className="st-badge st-resolved"><CheckCircle size={12}/> RESOLVED</span>;
      case 'remediation_failed':
        return <span className="st-badge st-failed"><AlertCircle size={12}/> REMEDIATION FAILED</span>;
      default:
        return <span className="st-badge">{st.toUpperCase()}</span>;
    }
  };

  return (
    <div className={`incident-card-root ${status === 'remediation_failed' ? 'card-failed' : ''}`}>
      {/* Top Bar */}
      <div className="card-top-bar">
        <div className="card-header-info">
          <span className="incident-id-tag">{incident_id}</span>
          <SeverityBadge severity={severity} />
          {getStatusBadge(status)}
        </div>
        <div className="card-duration">
          <Clock size={14} />
          <span>Duration: {elapsed}s</span>
        </div>
      </div>

      {/* Scenario & Primary Info */}
      <div className="card-main-grid">
        <div className="meta-box">
          <span className="meta-label">Scenario</span>
          <span className="meta-value highlight-cyan">{scenario}</span>
        </div>
        <div className="meta-box">
          <span className="meta-label">Triggered At</span>
          <span className="meta-value">{start_time}</span>
        </div>
        <div className="meta-box">
          <span className="meta-label">Affected Count</span>
          <span className="meta-value">{directSvc.length + downstreamSvc.length} Services</span>
        </div>
        <div className="meta-box">
          <span className="meta-label">Risk policy</span>
          <span className="meta-value">{incident.risk_level || 'Assessing'}</span>
        </div>
      </div>

      {/* Impacted Services Mapping */}
      <div className="card-services-section">
        <span className="meta-label">Blast Radius / Impact Analysis</span>
        <div className="services-map-chips">
          <div className="chip-group">
            <span className="chip-group-label">Direct:</span>
            {directSvc.map(svc => (
              <span key={svc} className="svc-chip direct-chip">
                <Server size={12} /> {svc}
              </span>
            ))}
          </div>
          {downstreamSvc.length > 0 && (
            <div className="chip-group">
              <span className="chip-group-label"><ArrowRight size={12} /> Downstream:</span>
              {downstreamSvc.map(svc => (
                <span key={svc} className="svc-chip downstream-chip">
                  {svc}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Symptoms & Root Cause */}
      <div className="card-details-box">
        <div className="detail-item">
          <span className="detail-title">Symptoms:</span>
          <span className="detail-text">{symptoms || 'Evaluating metric baseline...'}</span>
        </div>
        <div className="detail-item">
          <span className="detail-title">Root Cause:</span>
          <span className="detail-text highlight-purple">{root_cause || 'Investigating...'}</span>
        </div>
        {incident.recommended_remediation && incident.recommended_remediation !== 'Pending analysis...' && (
          <div className="detail-item">
            <span className="detail-title">Recommended Recovery:</span>
            <span className="detail-text">{incident.recommended_remediation}</span>
          </div>
        )}
        {executed_action && executed_action !== 'None' && (
          <div className="detail-item">
            <span className="detail-title">Executed Fix:</span>
            <span className="detail-text highlight-green">{executed_action}</span>
          </div>
        )}
      </div>

        {status === 'remediation_failed' && (
        <div className="failure-banner">
          <AlertCircle size={18} />
          <span>Automated remediation was unable to recover the system. Human intervention required!</span>
        </div>
      )}
    </div>
  );
};

export default IncidentCard;
