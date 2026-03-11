import React from 'react';
import Plot from 'react-plotly.js';
import './ChartAnimations.css';

export default function ChartRenderer({ queryInfo }) {
  const { title, data, chart_type, x_axis, y_axis, group_by } = queryInfo;
  
  if (!data || data.length === 0) {
    return <div style={{padding: '1rem', color: 'var(--text-muted)'}}>No data returned.</div>;
  }

  // Common Layout
  const layout = {
    title: { text: title, font: { color: '#FFFFFF', size: 18 } },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: 'Inter', color: '#FFFFFF' },
    margin: { l: 40, r: 20, t: 60, b: 40 },
    height: 400,
    autosize: true,
    xaxis: { 
      title: x_axis,
      gridcolor: '#475569',
      zerolinecolor: '#475569',
      linecolor: '#475569'
    },
    yaxis: { 
      title: y_axis,
      gridcolor: '#475569',
      zerolinecolor: '#475569',
      linecolor: '#475569'
    },
  };

  const config = { responsive: true, displayModeBar: false };
  let trace = {};

  // Data processing based on groups
  let groupedData = {};
  if (group_by && data[0] && group_by in data[0]) {
    data.forEach(row => {
      const g = row[group_by];
      if (!groupedData[g]) {
        groupedData[g] = { x: [], y: [] };
      }
      groupedData[g].x.push(row[x_axis]);
      groupedData[g].y.push(row[y_axis]);
    });
  } else {
    groupedData['default'] = {
      x: data.map(r => r[x_axis]),
      y: data.map(r => r[y_axis])
    };
  }

  const themeColors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4'];
  const baseColor = '#3B82F6';

  const createTraces = (type, extra = {}) => {
    return Object.keys(groupedData).map((key, idx) => ({
      x: groupedData[key].x,
      y: groupedData[key].y,
      name: key !== 'default' ? String(key) : undefined,
      type: type,
      marker: { color: key === 'default' ? baseColor : themeColors[idx % themeColors.length] },
      ...extra
    }));
  };

  let traces = [];

  switch (chart_type) {
    case 'line':
      traces = createTraces('scatter', { mode: 'lines+markers' });
      break;
    case 'scatter':
      traces = createTraces('scatter', { mode: 'markers' });
      break;
    case 'bar':
      traces = createTraces('bar', { textposition: 'outside' });
      break;
    case 'pie':
      traces = [{
        values: groupedData['default'].y,
        labels: groupedData['default'].x,
        type: 'pie',
        hole: 0.3,
        marker: { colors: themeColors }
      }];
      break;
    case 'funnel':
      traces = createTraces('funnel');
      break;
    case 'heatmap':
      // Basic heatmap proxy using density
      traces = [{
        x: data.map(r => r[x_axis]),
        y: data.map(r => r[y_axis]),
        z: group_by ? data.map(r => r[group_by]) : undefined,
        type: 'histogram2d',
        colorscale: [
          [0, '#1E293B'],
          [1, baseColor]
        ]
      }];
      break;
    case 'none':
    default:
      // Render as a simple table or KPI if 'none'
      return (
        <div style={{ background: 'var(--bg-tertiary)', padding: '1rem', borderRadius: '8px' }}>
          <h4>{title}</h4>
          <pre style={{ color: 'var(--accent-hover)' }}>
            {JSON.stringify(data.slice(0, 5), null, 2)}
          </pre>
        </div>
      );
  }

  return (
    <div style={{ width: '100%', border: '1px solid var(--border)', borderRadius: '8px', overflow: 'hidden', background: 'var(--bg-secondary)', marginBottom: '1rem' }}>
      <Plot
        data={traces}
        layout={layout}
        config={config}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler={true}
      />
    </div>
  );
}
