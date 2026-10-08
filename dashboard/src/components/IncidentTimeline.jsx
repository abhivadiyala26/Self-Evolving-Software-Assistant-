import React from 'react';
import { Clock, CheckCircle2, AlertTriangle, Shield, Cpu, RefreshCw } from 'lucide-react';
import './IncidentManagement.css';

const IncidentTimeline = ({ timeline = [], currentStatus = 'healthy' }) => {
  const getStageIcon = (stage = '') => {
    if (stage.includes('Chaos')) return <AlertTriangle size={15} color="#a34d44" />;
    if (stage.includes('Detection')) return <Clock size={15} color="#607367" />;
    if (stage.includes('Analysis')) return <Cpu size={15} color="#607367" />;
    if (stage.includes('Root Cause')) return <AlertTriangle size={15} color="#80694f" />;
    if (stage.includes('Remediation')) return <Shield size={15} color="#607367" />;
    if (stage.includes('Deployment')) return <RefreshCw size={15} color="#80694f" />;
    if (stage.includes('Resolved') || stage.includes('Closure')) return <CheckCircle2 size={15} color="#34745b" />;
    return <Clock size={15} color="#788279" />;
  };

  if (!timeline || timeline.length === 0) {
    return (
      <div className="empty-timeline">
        <span>No active incident timeline recorded. Trigger chaos to start tracking.</span>
      </div>
    );
  }

  return (
    <div className={`incident-timeline-root status-${currentStatus}`}>
      <div className="timeline-list">
        {timeline.map((event, idx) => (
          <div key={idx} className="timeline-item animate-fade-in">
            <div className="timeline-marker">
              <div className="marker-icon">
                {getStageIcon(event.stage)}
              </div>
              {idx < timeline.length - 1 && <div className="timeline-line" />}
            </div>

            <div className="timeline-content">
              <div className="timeline-header">
                <span className="timeline-title">{event.title}</span>
                <span className="timeline-time">{event.timestamp}</span>
              </div>
              <p className="timeline-desc">{event.description}</p>
              {event.agent && (
                <div className="timeline-badge">
                  <span>Agent: {event.agent}</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default IncidentTimeline;
