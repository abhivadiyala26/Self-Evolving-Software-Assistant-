import React from 'react';

const SeverityBadge = ({ severity = 'P4' }) => {
  const normalized = severity.toUpperCase();
  const labels = { P1: 'Critical', P2: 'High', P3: 'Moderate', P4: 'Low' };
  return <span className={`severity-badge severity-${normalized.toLowerCase()}`}>{normalized} · {labels[normalized] || 'Unclassified'}</span>;
};

export default SeverityBadge;
