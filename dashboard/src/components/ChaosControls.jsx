import React, { useState } from 'react';
import { AlertOctagon, RotateCcw } from 'lucide-react';

const scenarios = [
  ['payment_crash', 'Payment service crash', 'paymentservice'],
  ['payment_high_latency', 'Payment latency degradation', 'paymentservice'],
  ['frontend_spike', 'Frontend traffic spike', 'frontend'],
  ['database_failure', 'Database connection failure', 'database'],
  ['service_crash', 'Stop a service', 'frontend'],
  ['api_error_spike', 'API error spike', 'paymentservice'],
  ['cpu_spike', 'CPU saturation', 'frontend'],
  ['memory_spike', 'Memory pressure', 'database'],
  ['network_timeout', 'Network timeout', 'checkoutservice'],
];

const serviceOptions = ['frontend', 'authservice', 'cartservice', 'checkoutservice', 'recommendationservice', 'productcatalogservice', 'paymentservice', 'shippingservice', 'emailservice', 'currencyservice', 'adservice', 'database'];

const ChaosControls = ({ systemState, setSystemState }) => {
  const [scenario, setScenario] = useState(scenarios[0][0]);
  const [service, setService] = useState(scenarios[0][2]);
  const [triggering, setTriggering] = useState(false);
  const selectedScenario = scenarios.find(([key]) => key === scenario);
  const requiresTarget = ['service_crash', 'api_error_spike', 'cpu_spike', 'memory_spike', 'network_timeout'].includes(scenario);

  const triggerFailure = async () => {
    if (systemState !== 'healthy') return;
    setTriggering(true);
    try {
      const response = await fetch('http://localhost:8000/api/trigger_chaos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-admin-token': localStorage.getItem('adminToken') || '' },
        body: JSON.stringify({ scenario, service: requiresTarget ? service : null }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || 'The backend rejected the scenario.');
      }
      setSystemState('anomaly');
    } catch (error) {
      window.alert(error.message || 'Could not reach the AutoSRE backend.');
    } finally {
      setTriggering(false);
    }
  };

  const resetSystem = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/reset', { method: 'POST', headers: { 'x-admin-token': localStorage.getItem('adminToken') || '' } });
      if (!response.ok) throw new Error('Reset was rejected by the backend.');
      setSystemState('healthy');
    } catch (error) {
      window.alert(error.message || 'Could not reset the demo.');
    }
  };

  return (
    <div className="chaos-controls">
      <div className="chaos-form-row">
        <label>Scenario<select value={scenario} onChange={(event) => {
          const choice = scenarios.find(([key]) => key === event.target.value);
          setScenario(event.target.value);
          setService(choice?.[2] || 'frontend');
        }}>{scenarios.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
        {requiresTarget && <label>Target service<select value={service} onChange={(event) => setService(event.target.value)}>{serviceOptions.map((name) => <option key={name} value={name}>{name}</option>)}</select></label>}
        <button className="button-primary" onClick={triggerFailure} disabled={systemState !== 'healthy' || triggering}><AlertOctagon size={15} />{triggering ? 'Injecting…' : 'Inject scenario'}</button>
        <button className="button-secondary" onClick={resetSystem}><RotateCcw size={15} />Reset demo</button>
      </div>
      <p className="chaos-policy-note">The background agent detects the sustained signal, analyzes impact, and recovers medium-risk incidents automatically. High-risk changes wait for approval.</p>
      {selectedScenario && <small className="chaos-selected-note">Selected: {selectedScenario[1]}</small>}
    </div>
  );
};

export default ChaosControls;
