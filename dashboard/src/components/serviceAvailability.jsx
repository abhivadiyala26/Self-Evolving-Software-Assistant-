import { SERVICE_LABELS } from './serviceStatus';
import './ServiceAvailability.css';

export const ServiceAvailabilityNotice = ({ services = [] }) => {
  if (!services.length) return null;
  const labels = services.map((service) => SERVICE_LABELS[service] || service);
  const unavailableText = labels.length === 1
    ? `${labels[0]} service is temporarily unavailable.`
    : `${labels.slice(0, -1).join(', ')} and ${labels[labels.length - 1]} services are temporarily unavailable.`;

  return (
    <div className="service-availability-notice" role="status" aria-live="polite">
      <strong>⚠ {unavailableText}</strong>
      <span>Some features may be unavailable until recovery is verified.</span>
    </div>
  );
};
