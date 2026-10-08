import React, { useState } from 'react';
import SeverityBadge from './SeverityBadge';
import IncidentTimeline from './IncidentTimeline';
import { Eye, X, History, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import './IncidentManagement.css';

const IncidentHistory = ({ incidents = [], onSelectIncident }) => {
  const [selectedIncident, setSelectedIncident] = useState(null);

  const handleOpenModal = (inc) => {
    setSelectedIncident(inc);
    if (onSelectIncident) onSelectIncident(inc);
  };

  const handleCloseModal = () => {
    setSelectedIncident(null);
  };

  return (
    <div className="incident-history-root">
      <div className="history-header">
        <div className="history-title">
          <History size={20} color="var(--accent-cyan)" />
          <h3>Incident History Log</h3>
        </div>
        <span className="history-count">{incidents.length} Total Records</span>
      </div>

      {incidents.length === 0 ? (
        <div className="history-empty">
          <span>No historical incidents recorded yet.</span>
        </div>
      ) : (
        <div className="history-table-wrapper">
          <table className="history-table">
            <thead>
              <tr>
                <th>Incident ID</th>
                <th>Date</th>
                <th>Service</th>
                <th>Issue</th>
                <th>Severity</th>
                <th>Root Cause</th>
                <th>Duration</th>
                <th>Recovery Action</th>
                <th>Status</th>
                <th>Resolved By</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {incidents.map((inc) => (
                <tr key={inc.incident_id} className="history-row" onClick={() => handleOpenModal(inc)}>
                  <td className="font-mono highlight-cyan">{inc.incident_id}</td>
                  <td>{inc.start_time || inc.timestamp}</td>
                  <td>{inc.affected_services?.directly_affected?.[0] || '—'}</td>
                  <td>{inc.scenario}</td>
                  <td><SeverityBadge severity={inc.severity} /></td>
                  <td className="root-cause-cell">{inc.root_cause || 'N/A'}</td>
                  <td>{inc.total_duration ? `${inc.total_duration}s` : 'Active'}</td>
                  <td>{inc.executed_action && inc.executed_action !== 'None' ? inc.executed_action : inc.recommended_remediation || 'Pending'}</td>
                  <td>
                    <span className={`hist-status-pill status-${inc.status}`}>
                      {inc.status === 'resolved' && <CheckCircle size={12} />}
                      {inc.status === 'remediation_failed' && <AlertCircle size={12} />}
                      {inc.status !== 'resolved' && inc.status !== 'remediation_failed' && <Clock size={12} />}
                      {inc.status.toUpperCase()}
                    </span>
                  </td>
                  <td>{inc.status === 'resolved' ? (inc.auto_recovered ? 'AutoSRE' : inc.approval_status === 'approved' ? 'Admin-approved' : 'Administrator') : '—'}</td>
                  <td>
                    <button className="btn-view-details" onClick={(e) => { e.stopPropagation(); handleOpenModal(inc); }}>
                      <Eye size={14} /> View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Incident Detail Modal */}
      {selectedIncident && (
        <div className="modal-backdrop" onClick={handleCloseModal}>
          <div className="modal-content animate-fade-in" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-group">
                <h3>Incident Details: {selectedIncident.incident_id}</h3>
                <SeverityBadge severity={selectedIncident.severity} />
              </div>
              <button className="modal-close-btn" onClick={handleCloseModal}>
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              <div className="modal-meta-grid">
                <div className="modal-meta-item">
                  <span className="label">Scenario:</span>
                  <span className="val">{selectedIncident.scenario}</span>
                </div>
                <div className="modal-meta-item">
                  <span className="label">Start Time:</span>
                  <span className="val">{selectedIncident.start_time}</span>
                </div>
                <div className="modal-meta-item">
                  <span className="label">Resolution Time:</span>
                  <span className="val">{selectedIncident.resolution_time || 'Active / Unresolved'}</span>
                </div>
                <div className="modal-meta-item">
                  <span className="label">Total Duration:</span>
                  <span className="val">{selectedIncident.total_duration ? `${selectedIncident.total_duration} seconds` : 'In Progress'}</span>
                </div>
              </div>

              <div className="modal-section">
                <h4>Root Cause Analysis</h4>
                <p className="modal-text">{selectedIncident.root_cause}</p>
              </div>

              <div className="modal-section">
                <h4>Executed Action</h4>
                <p className="modal-text highlight-green">{selectedIncident.executed_action || 'None'}</p>
              </div>

              <div className="modal-section">
                <h4>Complete Timeline</h4>
                <IncidentTimeline timeline={selectedIncident.timeline} currentStatus={selectedIncident.status} />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default IncidentHistory;
