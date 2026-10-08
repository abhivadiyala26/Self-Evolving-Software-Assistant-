import { useEffect, useState } from 'react';
import { API_URL } from '../api';

export const SERVICE_LABELS = {
  frontend: 'Frontend',
  productcatalogservice: 'Product',
  cartservice: 'Cart',
  checkoutservice: 'Order',
  paymentservice: 'Payment',
};

export const isServiceUnavailable = (statuses, serviceId) => {
  const status = statuses?.[serviceId];
  return Boolean(status && status !== 'healthy');
};

export const useServiceStatuses = () => {
  const [health, setHealth] = useState({ statuses: {}, ready: false });

  useEffect(() => {
    let active = true;
    const pollServices = async () => {
      try {
        const response = await fetch(`${API_URL}/services`);
        if (!response.ok) return;
        const services = await response.json();
        if (!active || !Array.isArray(services)) return;
        setHealth({
          statuses: Object.fromEntries(services.map(({ id, status }) => [id, status])),
          ready: true,
        });
      } catch {
        // Keep the last backend-reported states until the next health poll succeeds.
      }
    };

    pollServices();
    const interval = setInterval(pollServices, 1500);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  return health;
};
