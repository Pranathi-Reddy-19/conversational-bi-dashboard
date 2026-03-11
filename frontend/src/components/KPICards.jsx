import React from 'react';
import './KPICards.css';

export default function KPICards({ kpis }) {
  if (!kpis || kpis.length === 0) return null;

  return (
    <div className="kpi-grid">
      {kpis.map((kpi, idx) => (
        <div key={idx} className="kpi-card glass-panel">
          <div className="kpi-value">{kpi.value}</div>
          <div className="kpi-label">{kpi.label}</div>
        </div>
      ))}
    </div>
  );
}
