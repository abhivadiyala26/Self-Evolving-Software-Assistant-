import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

const chartColor = '#34745b';
const grid = <CartesianGrid stroke="#e8ece7" vertical={false} />;
const axis = { stroke: '#89918a', fontSize: 10, tickLine: false, axisLine: false };
const tooltip = { contentStyle: { background: '#fff', border: '1px solid #dfe4de', borderRadius: 5, fontSize: 11 }, itemStyle: { color: '#34745b' }, labelStyle: { color: '#5e685f' } };

const ChartPanel = ({ title, data, dataKey, name, unit = '', threshold }) => (
  <div className="chart-panel">
    <strong>{title}</strong>
    <div className="chart-plot">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
          {grid}<XAxis dataKey="time" hide /><YAxis {...axis} tickFormatter={(value) => `${value}${unit}`} /><Tooltip {...tooltip} />
          {threshold !== undefined && <ReferenceLine y={threshold} stroke="#b87926" strokeDasharray="4 4" />}
          <Line type="monotone" dataKey={dataKey} name={name} stroke={chartColor} strokeWidth={1.8} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  </div>
);

const ObservabilityChart = ({ data = [], compact = false }) => (
  <div className={`observability-chart-grid${compact ? ' compact' : ''}`}>
    <ChartPanel title="Payment latency · p95" data={data} dataKey="latency" name="p95 latency" unit="ms" threshold={500} />
    <ChartPanel title="Payment error rate" data={data} dataKey="errors" name="error rate" unit="%" threshold={5} />
    <ChartPanel title="Payment request rate" data={data} dataKey="requests" name="requests / sec" unit="/s" />
    <ChartPanel title="Payment CPU utilization" data={data} dataKey="cpu" name="CPU" unit="%" threshold={85} />
    {!compact && <ChartPanel title="Payment memory utilization" data={data} dataKey="memory" name="memory" unit="%" threshold={90} />}
    {!compact && <ChartPanel title="Database latency" data={data} dataKey="databaseLatency" name="database latency" unit="ms" />}
    {!compact && <ChartPanel title="Throughput" data={data} dataKey="throughput" name="throughput" unit=" MB/s" />}
    {!compact && <ChartPanel title="Active connections" data={data} dataKey="connections" name="connections" />}
    {!compact && <ChartPanel title="HTTP 5xx responses / sec" data={data} dataKey="http5xx" name="5xx / sec" />}
  </div>
);

export default ObservabilityChart;
