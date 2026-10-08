import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { API_URL } from '../api';
import './Dashboard.css';
import { Activity, Server, ShieldAlert, TerminalSquare, AlertCircle } from 'lucide-react';
import AgentTerminal from './AgentTerminal';
import TopologyMap from './TopologyMap';
import ObservabilityChart from './ObservabilityChart';
import ChaosControls from './ChaosControls';
import IncidentCard from './IncidentCard';
import IncidentTimeline from './IncidentTimeline';
import IncidentHistory from './IncidentHistory';

const getRouteTab = (path) => path.startsWith('/history') ? 'history' : path.startsWith('/incidents') ? 'timeline' : ['alerts', 'logs', 'metrics', 'services', 'agents'].includes(path.split('/')[1]) ? path.split('/')[1] : 'overview';

const Dashboard = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [systemState, setSystemState] = useState('healthy');
  const [uptimeSeconds, setUptimeSeconds] = useState(0);
  const [logs, setLogs] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [currentMetrics, setCurrentMetrics] = useState({});
  const [services, setServices] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [failingNode, setFailingNode] = useState(null);
  const [activeIncident, setActiveIncident] = useState(null);
  const [allIncidents, setAllIncidents] = useState([]);
  const activeTab = getRouteTab(location.pathname);
  const [agents, setAgents] = useState([]);
  const [backgroundStatus, setBackgroundStatus] = useState({ status: 'starting', activity: [] });
  const [selectedServiceId, setSelectedServiceId] = useState(null);
  const [decisionBusy, setDecisionBusy] = useState(false);
  const [metricWindow, setMetricWindow] = useState('60');
  const [toastAlert, setToastAlert] = useState(null);
  const [logFilters, setLogFilters] = useState({ service: '', level: '', incidentId: '', search: '', window: 'all' });
  const seenAlertIds = useRef(null);
  const toastTimer = useRef(null);

  const decideRecovery = async (decision) => {
    if (!activeIncident) return;
    setDecisionBusy(true);
    try {
      const res = await fetch(`${API_URL}/incidents/${activeIncident.incident_id}/${decision}-recovery`, {
        method: 'POST',
        headers: { 'x-admin-token': localStorage.getItem('adminToken') || '' }
      });
      if (!res.ok) {
        const body = await res.json();
        throw new Error(body.detail || 'Could not update the recovery decision.');
      }
    } catch (error) {
      window.alert(error.message || 'Could not reach the AutoSRE backend.');
    } finally {
      setDecisionBusy(false);
    }
  };

  const signOut = async () => {
    const token = localStorage.getItem('adminToken');
    if (token) await fetch(`${API_URL}/auth/logout`, { method: 'POST', headers: { 'x-admin-token': token } }).catch(() => {});
    localStorage.removeItem('adminToken');
    localStorage.removeItem('currentUser');
    navigate('/login');
  };

  // Poll backend for system status, active incident, history, logs, and metrics
  useEffect(() => {
    return () => clearTimeout(toastTimer.current);
  }, []);

  useEffect(() => {
    const pollBackend = async () => {
      try {
        const adminHeaders = { 'x-admin-token': localStorage.getItem('adminToken') || '' };
        const [statusRes, metricsRes, incidentsRes, logsRes, servicesRes, alertsRes, agentsRes, backgroundRes] = await Promise.all([
          fetch(`${API_URL}/status`),
          fetch(`${API_URL}/metrics`),
          fetch(`${API_URL}/incidents`, { headers: adminHeaders }),
          fetch(`${API_URL}/logs`, { headers: adminHeaders }),
          fetch(`${API_URL}/services`),
          fetch(`${API_URL}/alerts`, { headers: adminHeaders }),
          fetch(`${API_URL}/agents`, { headers: adminHeaders }),
          fetch(`${API_URL}/agent/status`, { headers: adminHeaders })
        ]);

        if (statusRes.ok) {
          const data = await statusRes.json();
          setSystemState(data.system_state);
          setUptimeSeconds(data.uptime_seconds || 0);
          if (data.system_state === 'healthy') setFailingNode(null);
        }

        if (incidentsRes.ok) {
          const incData = await incidentsRes.json();
          setAllIncidents(incData);
          setActiveIncident(incData.find((inc) => !['resolved', 'remediation_failed'].includes(inc.status)) || null);
        }
        if (logsRes.ok) setLogs(await logsRes.json());
        if (alertsRes.ok) {
          const alertData = await alertsRes.json();
          if (seenAlertIds.current !== null) {
            const newest = alertData.find((alert) => !seenAlertIds.current.has(alert.alert_id));
            if (newest) {
              setToastAlert(newest);
              clearTimeout(toastTimer.current);
              toastTimer.current = setTimeout(() => setToastAlert(null), 6500);
            }
          }
          seenAlertIds.current = new Set(alertData.map((alert) => alert.alert_id));
          setAlerts(alertData);
        }
        if (agentsRes.ok) setAgents(await agentsRes.json());
        if (backgroundRes.ok) setBackgroundStatus(await backgroundRes.json());
        if (servicesRes.ok) {
          const serviceData = await servicesRes.json();
          setServices(serviceData);
          const troubled = serviceData.find((svc) => svc.status !== 'healthy');
          setFailingNode(troubled ? troubled.id === 'paymentservice' ? 'payment' : troubled.id === 'database' ? 'database' : troubled.id : null);
        }

        if (metricsRes.ok) {
          const metricsData = await metricsRes.json();
          setCurrentMetrics(metricsData);

          setFailingNode(prev => {
            if (metricsData['paymentservice']?.error_rate > 50) return 'payment';
            if (metricsData['frontend']?.error_rate > 15) return 'frontend';
            return prev;
          });

          setMetrics(prev => {
            const newData = [...prev];
            if (newData.length > 60) newData.shift();

            const lastTime = newData.length > 0 ? newData[newData.length - 1].time : 0;
            const payment = metricsData['paymentservice'] || {latency_p95_ms: 0, error_rate: 0};
            const frontend = metricsData['frontend'] || {latency_p95_ms: 0, error_rate: 0};

            newData.push({
              time: lastTime + 1,
              latency: payment.latency_p95_ms,
              frontendLatency: frontend.latency_p95_ms,
              errors: payment.error_rate,
              requests: payment.requests_per_sec,
              cpu: payment.cpu_percent,
              memory: payment.memory_percent,
              databaseLatency: metricsData.database?.latency_p95_ms || 0,
              throughput: payment.throughput_mbps || 0,
              connections: payment.active_connections || 0,
              http5xx: payment.http_5xx_per_sec || 0
            });
            return newData;
          });
        }
      } catch {
        console.error('Backend not reachable. Check VITE_API_BASE_URL and confirm the API is running.');
      }
    };

    const intervalId = setInterval(pollBackend, 1000);
    return () => clearInterval(intervalId);
  }, []);

  const acknowledgeAlert = async (alertId) => {
    try {
      const response = await fetch(`${API_URL}/alerts/${alertId}/acknowledge`, {
        method: 'POST',
        headers: { 'x-admin-token': localStorage.getItem('adminToken') || '' }
      });
      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail || 'Could not acknowledge alert.');
      }
      const alertResponse = await fetch(`${API_URL}/alerts`, { headers: { 'x-admin-token': localStorage.getItem('adminToken') || '' } });
      if (alertResponse.ok) setAlerts(await alertResponse.json());
    } catch (error) {
      window.alert(error.message || 'Could not reach the AutoSRE backend.');
    }
  };

  const incidentIdFromPath = location.pathname.startsWith('/incidents/') ? location.pathname.split('/')[2] : null;
  const focusedIncident = incidentIdFromPath ? allIncidents.find((incident) => incident.incident_id === incidentIdFromPath) || activeIncident : activeIncident;
  const showApproval = focusedIncident?.status === 'awaiting_approval' && focusedIncident?.approval_status === 'pending';
  const latestMetrics = metrics[metrics.length - 1] || {};
  const chartMetrics = metrics.slice(-Number(metricWindow));
  const serviceCounts = services.reduce((counts, service) => {
    counts[service.status] = (counts[service.status] || 0) + 1;
    return counts;
  }, {});
  const metricValues = Object.values(currentMetrics);
  const totalRps = metricValues.reduce((sum, value) => sum + (value.requests_per_sec || 0), 0);
  const averageLatency = metricValues.length ? Math.round(metricValues.reduce((sum, value) => sum + (value.latency_p95_ms || 0), 0) / metricValues.length) : 0;
  const weightedErrors = totalRps ? metricValues.reduce((sum, value) => sum + (value.requests_per_sec || 0) * (value.error_rate || 0), 0) / totalRps : 0;
  const errorAnalytics = {
    total5xx: metricValues.reduce((sum, value) => sum + (value.http_5xx_per_sec || 0), 0),
    total4xx: metricValues.reduce((sum, value) => sum + (value.http_4xx_per_sec || 0), 0),
    criticalServices: metricValues.filter((value) => value.error_rate >= 5).length,
    timeouts: metricValues.filter((value) => value.latency_p95_ms >= 1000).length,
    databaseErrors: currentMetrics.database?.http_5xx_per_sec || 0,
    failures: services.filter((service) => service.status === 'down').length,
  };
  const activeIncidents = allIncidents.filter((incident) => !['resolved', 'remediation_failed'].includes(incident.status)).length;
  const uptimeLabel = `${Math.floor(uptimeSeconds / 3600)}h ${Math.floor((uptimeSeconds % 3600) / 60)}m ${uptimeSeconds % 60}s`;
  const focusedServiceId = focusedIncident?.affected_services?.directly_affected?.[0];
  const focusedServiceMetrics = focusedServiceId ? currentMetrics[focusedServiceId] || {} : {};
  const focusedIncidentLogs = focusedIncident ? logs.filter((log) => log.incident_id === focusedIncident.incident_id).slice(-8).reverse() : [];
  const selectedService = services.find((service) => service.id === selectedServiceId) || null;
  const selectedServiceLogs = selectedService ? logs.filter((log) => log.service === selectedService.id).slice(-8).reverse() : [];
  const visibleLogs = logs.filter((log) => {
    if (logFilters.service && log.service !== logFilters.service) return false;
    if (logFilters.level && log.level !== logFilters.level) return false;
    if (logFilters.incidentId && log.incident_id !== logFilters.incidentId) return false;
    const query = logFilters.search.trim().toLowerCase();
    if (query && !`${log.message} ${log.agent} ${log.service}`.toLowerCase().includes(query)) return false;
    if (logFilters.window !== 'all' && log.time) {
      const duration = logFilters.window === '15m' ? 15 * 60 * 1000 : 60 * 60 * 1000;
      if (Date.now() - new Date(log.time).getTime() > duration) return false;
    }
    return true;
  });

  return (
    <div className="dashboard-root">
      {/* Top Header */}
      <header className="dashboard-header animate-fade-in">
        <div className="header-brand">
          <div className="brand-logo">
            <Activity size={22} />
          </div>
          <div>
            <h1>AutoSRE</h1>
            <span className="brand-subtitle">Operations</span>
          </div>
        </div>

        <div className="dashboard-tab-bar">
          {[
            ['overview', 'Overview', '/dashboard'], ['timeline', 'Incidents', '/incidents'],
            ['services', 'Services', '/services'], ['metrics', 'Metrics', '/metrics'],
            ['alerts', `Alerts ${alerts.filter((alert) => alert.status === 'firing').length || ''}`, '/alerts'],
            ['logs', 'Logs', '/logs'], ['agents', 'Agents', '/agents'], ['history', 'History', '/history'],
          ].map(([tab, label, path]) => (
            <button key={tab} className={`tab-btn ${activeTab === tab ? 'active' : ''}`} onClick={() => navigate(path)}>{label}</button>
          ))}
        </div>

        <div className="header-status">
          <div className={`status-indicator status-${systemState}`}>
            <span className="pulse-dot"></span>
            {systemState.toUpperCase()}
          </div>
          <button className="header-store-link" onClick={() => navigate('/')}>ShopSphere</button>
          <button className="header-signout" onClick={signOut}>Sign out</button>
        </div>
      </header>

      {toastAlert && (
        <div className="admin-alert-toast" role="status">
          <AlertCircle size={20} />
          <div><strong>{toastAlert.severity} alert · {toastAlert.service}</strong><span>{toastAlert.title}</span></div>
          {toastAlert.incident_id && <button onClick={() => navigate(`/incidents/${toastAlert.incident_id}`)}>View incident</button>}
          <button aria-label="Dismiss alert" onClick={() => setToastAlert(null)}>×</button>
        </div>
      )}

      <section className="system-summary-strip" aria-label="System summary">
        <div><span>Services</span><strong>{services.length}</strong><small>{serviceCounts.healthy || 0} healthy · {serviceCounts.degraded || 0} degraded · {serviceCounts.down || 0} down</small></div>
        <div><span>Active incidents</span><strong>{activeIncidents}</strong><small>{alerts.filter((alert) => alert.status === 'firing').length} firing alerts</small></div>
        <div><span>Average latency</span><strong>{averageLatency} ms</strong><small>Across simulated services</small></div>
        <div><span>Error rate</span><strong>{weightedErrors.toFixed(1)}%</strong><small>Request weighted</small></div>
        <div><span>Requests / sec</span><strong>{Math.round(totalRps).toLocaleString('en-IN')}</strong><small>Simulated throughput</small></div>
        <div><span>System uptime</span><strong>{uptimeLabel}</strong><small>Backend process runtime</small></div>
      </section>

      {activeTab === 'overview' && (
        <section className="background-agent-panel" aria-label="Background agent status">
          <div className="background-agent-heading"><span className="agent-running-mark" /><div><strong>Background agent</strong><small>Monitoring runs on the backend, independent of this dashboard.</small></div></div>
          <div className="background-agent-stat"><span>State</span><strong>{(backgroundStatus.status || 'starting').toUpperCase()}</strong></div>
          <div className="background-agent-stat"><span>Last cycle</span><strong>{backgroundStatus.last_cycle ? new Date(backgroundStatus.last_cycle).toLocaleTimeString() : 'Starting'}</strong></div>
          <div className="background-agent-stat"><span>Services</span><strong>{backgroundStatus.monitored_services || 0}</strong></div>
          <div className="background-agent-stat"><span>Auto recoveries</span><strong>{backgroundStatus.auto_recoveries || 0}</strong></div>
          <div className="background-agent-stat"><span>Escalations</span><strong>{backgroundStatus.escalations || 0}</strong></div>
          <div className="background-agent-last"><span>Last action</span><strong>{backgroundStatus.last_action || 'Collecting telemetry'}</strong></div>
          <div className="background-agent-activity"><span>Recent engineering activity</span>{(backgroundStatus.activity || []).slice(0, 4).map((item, index) => <article key={`${item.time}-${index}`}><time>{new Date(item.time).toLocaleTimeString()}</time><strong>{item.agent}</strong><span>{item.message}</span></article>)}{!backgroundStatus.activity?.length && <small>Waiting for a telemetry event.</small>}</div>
        </section>
      )}

      {/* Active Incident Banner (if an incident is currently active) */}
      {activeIncident && activeTab === 'overview' && (
        <section className="animate-fade-in">
          <IncidentCard incident={activeIncident} />
          {showApproval && (
            <div className="recovery-approval-panel">
              <div><strong>AWAITING ADMIN APPROVAL</strong><p>{activeIncident.recommended_remediation}</p></div>
              <div className="recovery-approval-actions">
                <button className="approve-recovery-btn" disabled={decisionBusy} onClick={() => decideRecovery('approve')}>Approve recovery</button>
                <button className="reject-recovery-btn" disabled={decisionBusy} onClick={() => decideRecovery('reject')}>Reject</button>
              </div>
            </div>
          )}
        </section>
      )}

      {/* Tab Content: Operations Overview */}
      {activeTab === 'overview' && (
        <div className="dashboard-grid">
          {/* Left Column: Observability & Topology */}
          <div className="grid-left">
            <section className="panel-card topology-panel">
              <div className="panel-header">
                <Server size={18} />
                <h2>Microservices Topology</h2>
              </div>
              <div className="panel-content">
                <TopologyMap systemState={systemState} failingNode={failingNode} services={services} />
              </div>
            </section>

            <section className="panel-card metrics-panel">
              <div className="panel-header">
                <Activity size={18} />
                <h2>Observability (Grafana View)</h2>
              </div>
              <div className="panel-content">
                <div className="service-metric-strip">
                  <div><span>PAYMENT RPS</span><strong>{latestMetrics.requests ?? '—'}</strong></div>
                  <div><span>CPU</span><strong>{latestMetrics.cpu ?? '—'}%</strong></div>
                  <div><span>MEMORY</span><strong>{latestMetrics.memory ?? '—'}%</strong></div>
                  <div><span>ERROR RATE</span><strong>{latestMetrics.errors ?? '—'}%</strong></div>
                </div>
                <ObservabilityChart data={metrics} systemState={systemState} compact />
              </div>
            </section>
          </div>

          {/* Right Column: AI Agents & Controls */}
          <div className="grid-right">
            <section className="panel-card controls-panel">
              <div className="panel-header">
                <ShieldAlert size={18} />
                <h2>Chaos Engineering & Demo Controls</h2>
              </div>
              <div className="panel-content">
                <ChaosControls
                  systemState={systemState}
                  setSystemState={setSystemState}
                />
              </div>
            </section>

            <section className="panel-card terminal-panel">
              <div className="panel-header">
                <TerminalSquare size={18} />
                <h2>Multi-Agent Terminal</h2>
              </div>
              <div className="panel-content">
                <AgentTerminal logs={logs} systemState={systemState} />
              </div>
            </section>
          </div>
        </div>
      )}

      {/* Tab Content: Active Incident & Timeline View */}
      {activeTab === 'timeline' && (
        <div className="dashboard-grid incident-tab-grid animate-fade-in">
          <div className="grid-left">
            <section className="panel-card">
              <div className="panel-header">
                <AlertCircle size={18} color="#607367" />
                <h2>Active Incident Overview</h2>
              </div>
              <div className="panel-content">
                <IncidentCard incident={focusedIncident} />
                {showApproval && focusedIncident && (
                  <div className="recovery-approval-panel">
                    <div><strong>AWAITING ADMIN APPROVAL</strong><p>{focusedIncident.recommended_remediation}</p></div>
                    <div className="recovery-approval-actions">
                      <button className="approve-recovery-btn" disabled={decisionBusy} onClick={() => decideRecovery('approve')}>Approve recovery</button>
                      <button className="reject-recovery-btn" disabled={decisionBusy} onClick={() => decideRecovery('reject')}>Reject</button>
                    </div>
                  </div>
                )}
              </div>
            </section>
          </div>

          <div className="grid-right">
            <section className="panel-card">
              <div className="panel-header">
                <Activity size={18} color="#607367" />
                <h2>Lifecycle Timeline & Agent Execution</h2>
              </div>
              <div className="panel-content">
                <IncidentTimeline
                  timeline={focusedIncident ? focusedIncident.timeline : []}
                  currentStatus={systemState}
                />
              </div>
            </section>
          </div>
        </div>
      )}

      {activeTab === 'timeline' && focusedIncident && (
        <section className="panel-card incident-context-panel animate-fade-in">
          <div className="panel-header"><AlertCircle size={18} /><h2>Incident details · {focusedIncident.incident_id}</h2></div>
          <div className="panel-content">
            <div className="incident-detail-grid">
              <article><span>Impact</span><strong>{focusedIncident.symptoms || 'Investigating service impact'}</strong><small>Affected: {[...(focusedIncident.affected_services?.directly_affected || []), ...(focusedIncident.affected_services?.downstream_affected || [])].join(', ') || 'Under investigation'}</small></article>
              <article><span>Root cause analysis</span><strong>{focusedIncident.root_cause || 'Agent analysis in progress'}</strong><small>{focusedIncident.evidence || 'Telemetry evidence is being collected.'}</small></article>
              <article><span>Recovery recommendation</span><strong>{focusedIncident.recommended_remediation || 'Pending agent analysis'}</strong><small>Approval: {focusedIncident.approval_status || 'pending'} · Recovery: {focusedIncident.recovery_status || focusedIncident.status}</small></article>
            </div>
            <div className="incident-detail-metrics">
              <div><span>CPU</span><strong>{focusedServiceMetrics.cpu_percent ?? '—'}%</strong></div>
              <div><span>Memory</span><strong>{focusedServiceMetrics.memory_percent ?? '—'}%</strong></div>
              <div><span>Latency</span><strong>{focusedServiceMetrics.latency_p95_ms ?? '—'} ms</strong></div>
              <div><span>Error rate</span><strong>{focusedServiceMetrics.error_rate ?? '—'}%</strong></div>
              <div><span>Requests / sec</span><strong>{focusedServiceMetrics.requests_per_sec ?? '—'}</strong></div>
            </div>
            <h3 className="incident-logs-title">Related logs · request and trace IDs</h3>
            <div className="incident-related-logs">{focusedIncidentLogs.length ? focusedIncidentLogs.map((log) => <article key={`${log.request_id}-${log.timestamp}`}><time>{log.timestamp}</time><strong>{log.level} · {log.service}</strong><span>{log.message}</span><small>Request {log.request_id || '—'} · Trace {log.trace_id || '—'}</small></article>) : <p>No correlated logs have been recorded yet.</p>}</div>
          </div>
        </section>
      )}

      {activeTab === 'alerts' && (
        <section className="panel-card admin-list-panel animate-fade-in">
          <div className="panel-header"><AlertCircle size={18} /><h2>Alert Center</h2><span>{alerts.length} total</span></div>
          <div className="admin-list-body">{alerts.length === 0 ? <p>No alerts are firing.</p> : alerts.map((alert) => <article className="admin-list-row" key={alert.alert_id}><span className={`alert-severity alert-${alert.severity}`}>{alert.severity}</span><div><strong>{alert.title}</strong><p>{alert.description}</p><small>{alert.service} · {new Date(alert.timestamp).toLocaleString()}</small></div><span>{alert.status}</span>{alert.incident_id && <button onClick={() => navigate(`/incidents/${alert.incident_id}`)}>{alert.incident_id}</button>}{alert.status === 'firing' && <button onClick={() => acknowledgeAlert(alert.alert_id)}>Acknowledge</button>}</article>)}</div>
        </section>
      )}

      {activeTab === 'logs' && <section className="panel-card admin-list-panel animate-fade-in"><div className="panel-header"><TerminalSquare size={18} /><h2>Service and Agent Logs</h2></div><div className="panel-content"><div className="log-filter-row"><input aria-label="Search logs" placeholder="Search message, service, agent…" value={logFilters.search} onChange={(event) => setLogFilters((prev) => ({ ...prev, search: event.target.value }))} /><select aria-label="Filter by service" value={logFilters.service} onChange={(event) => setLogFilters((prev) => ({ ...prev, service: event.target.value }))}><option value="">All services</option>{services.map((service) => <option key={service.id} value={service.id}>{service.name}</option>)}</select><select aria-label="Filter by severity" value={logFilters.level} onChange={(event) => setLogFilters((prev) => ({ ...prev, level: event.target.value }))}><option value="">All levels</option>{['INFO', 'WARNING', 'ERROR', 'CRITICAL'].map((level) => <option key={level}>{level}</option>)}</select><select aria-label="Filter by incident" value={logFilters.incidentId} onChange={(event) => setLogFilters((prev) => ({ ...prev, incidentId: event.target.value }))}><option value="">All incidents</option>{[...new Set(logs.map((log) => log.incident_id).filter(Boolean))].map((id) => <option key={id}>{id}</option>)}</select><select aria-label="Filter by time" value={logFilters.window} onChange={(event) => setLogFilters((prev) => ({ ...prev, window: event.target.value }))}><option value="all">Any time</option><option value="1h">Last hour</option><option value="15m">Last 15 minutes</option></select><span>{visibleLogs.length} logs</span></div><AgentTerminal logs={visibleLogs} systemState={systemState} /></div></section>}

      {activeTab === 'metrics' && <section className="panel-card admin-list-panel animate-fade-in"><div className="panel-header"><Activity size={18} /><h2>Metrics Explorer</h2><label className="metric-range-control">Time range<select value={metricWindow} onChange={(event) => setMetricWindow(event.target.value)}><option value="15">Last 15 seconds</option><option value="30">Last 30 seconds</option><option value="60">Last 60 seconds</option></select></label></div><div className="panel-content"><div className="service-metric-strip"><div><span>PAYMENT RPS</span><strong>{latestMetrics.requests ?? '—'}</strong></div><div><span>CPU</span><strong>{latestMetrics.cpu ?? '—'}%</strong></div><div><span>MEMORY</span><strong>{latestMetrics.memory ?? '—'}%</strong></div><div><span>ERROR RATE</span><strong>{latestMetrics.errors ?? '—'}%</strong></div></div><ObservabilityChart data={chartMetrics} systemState={systemState} /><section className="error-analytics"><h3>Error analytics · current simulated window</h3><div className="error-analytics-grid"><article><span>Estimated HTTP 5xx / sec</span><strong>{errorAnalytics.total5xx.toFixed(1)}</strong></article><article><span>Estimated HTTP 4xx / sec</span><strong>{errorAnalytics.total4xx.toFixed(1)}</strong></article><article><span>Services above 5% errors</span><strong>{errorAnalytics.criticalServices}</strong></article><article><span>Services over 1s latency</span><strong>{errorAnalytics.timeouts}</strong></article><article><span>Database 5xx / sec</span><strong>{errorAnalytics.databaseErrors.toFixed(1)}</strong></article><article><span>Failed services</span><strong>{errorAnalytics.failures}</strong></article></div></section></div></section>}

      {activeTab === 'services' && <>
        <section className="panel-card admin-list-panel animate-fade-in"><div className="panel-header"><Server size={18} /><h2>Service Health</h2><span>{services.length} monitored</span></div><div className="admin-list-body service-health-scroll"><table className="service-health-table"><thead><tr><th>Service</th><th>Status</th><th>CPU</th><th>Memory</th><th>Req/s</th><th>Error</th><th>Latency</th><th>Uptime</th><th>Replicas</th><th>Alerts</th><th>Last Check</th><th>Dependencies</th></tr></thead><tbody>{services.map((service) => <tr key={service.id} className={selectedServiceId === service.id ? 'selected-service-row' : ''}><td><button className="service-name-button" onClick={() => setSelectedServiceId(service.id)}>{service.name}</button></td><td><span className={`service-state-pill service-${service.status}`}>{service.status}</span></td><td>{service.cpu_percent}%</td><td>{service.memory_percent}%</td><td>{service.requests_per_sec}</td><td>{service.error_rate}%</td><td>{service.latency_p95_ms} ms</td><td>{service.uptime_percent}%</td><td>{service.replicas}</td><td>{alerts.filter((alert) => alert.service === service.id && alert.status === 'firing').length}</td><td>{new Date(service.last_health_check).toLocaleTimeString()}</td><td>{service.dependencies.join(', ') || '—'}</td></tr>)}</tbody></table></div></section>
        {selectedService && <section className="panel-card service-detail-panel"><div className="panel-header"><Server size={17} /><h2>{selectedService.name} · service detail</h2><span className={`service-state-pill service-${selectedService.status}`}>{selectedService.status}</span></div><div className="panel-content"><div className="service-detail-metrics"><div><span>CPU</span><strong>{selectedService.cpu_percent}%</strong></div><div><span>Memory</span><strong>{selectedService.memory_percent}%</strong></div><div><span>Requests / sec</span><strong>{selectedService.requests_per_sec}</strong></div><div><span>Error rate</span><strong>{selectedService.error_rate}%</strong></div><div><span>p95 latency</span><strong>{selectedService.latency_p95_ms} ms</strong></div><div><span>Replicas</span><strong>{selectedService.replicas}</strong></div></div><div className="service-detail-relations"><article><span>Depends on</span><strong>{selectedService.dependencies.join(', ') || 'No upstream dependencies'}</strong></article><article><span>Dependents</span><strong>{services.filter((service) => service.dependencies.includes(selectedService.id)).map((service) => service.name).join(', ') || 'No dependent services'}</strong></article></div><div className="service-detail-logs"><h3>Recent logs</h3>{selectedServiceLogs.length ? selectedServiceLogs.map((log, index) => <article key={`${log.request_id}-${index}`}><time>{log.timestamp}</time><span className={`log-level log-level-${log.level.toLowerCase()}`}>{log.level}</span><p>{log.message}</p></article>) : <small>No recent logs for this service.</small>}</div></div></section>}
      </>}

      {activeTab === 'agents' && <section className="panel-card admin-list-panel animate-fade-in"><div className="panel-header"><Activity size={18} /><h2>Multi-Agent Activity</h2></div><div className="agent-status-grid">{agents.map((agent) => <article key={agent.name}><strong>{agent.name}</strong><span className={`service-state-pill service-${agent.status === 'active' ? 'healthy' : 'degraded'}`}>{agent.status}</span><small>{agent.current_task}</small><time>{agent.timestamp ? new Date(agent.timestamp).toLocaleTimeString() : 'Idle'}</time></article>)}</div><div className="panel-content"><AgentTerminal logs={logs} systemState={systemState} /></div></section>}

      {/* Tab Content: Incident History Log */}
      {activeTab === 'history' && (
        <div className="animate-fade-in">
          <IncidentHistory incidents={allIncidents} onSelectIncident={(incident) => navigate(`/incidents/${incident.incident_id}`)} />
        </div>
      )}
    </div>
  );
};

export default Dashboard;
