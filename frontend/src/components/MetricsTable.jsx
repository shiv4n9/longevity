import React from 'react'

function MetricsTable({ metrics }) {
  if (!metrics || metrics.length === 0) {
    return null
  }

  const getHealthStatus = (metric) => {
    const cpu = metric.cpu_usage || 0
    const mem = metric.memory_usage || 0
    const hasData = metric.junos_version !== null

    if (!hasData) return { status: 'unknown', icon: '⚪', label: 'No Data' }
    if (cpu > 80 || mem > 80 || metric.has_core_dumps) return { status: 'critical', icon: '🔴', label: 'Critical' }
    if (cpu > 60 || mem > 60) return { status: 'warning', icon: '🟡', label: 'Warning' }
    return { status: 'healthy', icon: '🟢', label: 'Healthy' }
  }

  const getDeviceTypeLabel = (hostname) => {
    if (hostname.includes('vsrx')) return 'vSRX'
    if (hostname.includes('4100') || hostname.includes('5800')) return 'High-End SRX'
    if (hostname.includes('380')) return 'Branch SRX'
    return 'SRX Device'
  }

  const formatNumber = (num) => {
    if (num === null || num === undefined) return 'N/A'
    return num.toLocaleString()
  }

  const formatPercentage = (value) => {
    if (value === null || value === undefined) return 'N/A'
    return `${value}%`
  }

  const getPercentageClass = (value, warningThreshold = 60, criticalThreshold = 80) => {
    if (value === null || value === undefined) return ''
    if (value >= criticalThreshold) return 'critical'
    if (value >= warningThreshold) return 'warning'
    return 'good'
  }

  return (
    <div className="metrics-container">
      <div className="metrics-grid">
        {metrics.map((metric, idx) => {
          const health = getHealthStatus(metric)
          return (
            <div key={idx} className={`device-card ${health.status}`}>
              <div className="card-header">
                <div className="device-info">
                  <div className="device-name">
                    {metric.device_name || metric.hostname}
                  </div>
                  <div className="device-model">{getDeviceTypeLabel(metric.hostname)} • {metric.model || 'Unknown Model'}</div>
                </div>
                <div className={`health-badge ${health.status}`}>
                  <span className="health-icon">{health.icon}</span>
                  <span className="health-label">{health.label}</span>
                </div>
              </div>

              <div className="card-body">
                <div className="metric-row">
                  <div className="metric-item">
                    <div className="metric-label">Junos Version</div>
                    <div className="metric-value">{metric.junos_version || 'N/A'}</div>
                  </div>
                  <div className="metric-item">
                    <div className="metric-label">Routing Engine</div>
                    <div className="metric-value">{metric.routing_engine || 'N/A'}</div>
                  </div>
                </div>

                <div className="metric-row">
                  <div className="metric-item">
                    <div className="metric-label">CPU Usage</div>
                    <div className={`metric-value ${getPercentageClass(metric.cpu_usage)}`}>
                      {formatPercentage(metric.cpu_usage)}
                    </div>
                  </div>
                  <div className="metric-item">
                    <div className="metric-label">Memory Usage</div>
                    <div className={`metric-value ${getPercentageClass(metric.memory_usage)}`}>
                      {formatPercentage(metric.memory_usage)}
                    </div>
                  </div>
                </div>

                <div className="metric-row">
                  <div className="metric-item">
                    <div className="metric-label">Flow Sessions</div>
                    <div className="metric-value">{formatNumber(metric.flow_session_current)}</div>
                  </div>
                  <div className="metric-item">
                    <div className="metric-label">CP Sessions</div>
                    <div className="metric-value">{formatNumber(metric.cp_session_current)}</div>
                  </div>
                </div>

                <div className="metric-row">
                  <div className="metric-item">
                    <div className="metric-label">Core Dumps</div>
                    <div className={`metric-value ${metric.has_core_dumps ? 'critical' : 'good'}`}>
                      {metric.has_core_dumps ? 'Yes' : 'No'}
                    </div>
                  </div>
                  <div className="metric-item">
                    <div className="metric-label">Global SHM</div>
                    <div className={`metric-value ${getPercentageClass(metric.global_data_shm_percent, 50, 70)}`}>
                      {formatPercentage(metric.global_data_shm_percent)}
                    </div>
                  </div>
                </div>
              </div>

              <div className="card-footer">
                <div className="timestamp">
                  Last updated: {new Date(metric.timestamp).toLocaleString()}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default MetricsTable
