import { useState, useEffect } from 'react'
import axios from 'axios'
import './App.css'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
axios.defaults.baseURL = API_BASE

function Tooltip({ text, children }) {
  return (
    <div className="tooltip-container">
      {children}
      <div className="tooltip-text">{text}</div>
    </div>
  )
}

function App() {
  const [metric, setMetric] = useState(null)
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(null)
  const [collectionTime, setCollectionTime] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [autoRefresh, setAutoRefresh] = useState(false)

  useEffect(() => {
    loadMetric()
  }, [])

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        handleRefresh()
      }, 60000)
      return () => clearInterval(interval)
    }
  }, [autoRefresh])

  const loadMetric = async () => {
    try {
      const response = await axios.get('/api/v1/metrics/latest')
      const data = response.data || []
      const device = data.find(d => d.device_name === 'snpsrx4100c' || d.hostname.includes('snpsrx4100c'))
      setMetric(device || null)
      setLastUpdated(new Date())
    } catch (error) {
      console.error('Failed to load metrics:', error)
      setMetric(null)
    }
  }

  const handleRefresh = async () => {
    setLoading(true)
    setProgress('Establishing High-Speed Channel...')
    const startTime = Date.now()
    
    try {
      const response = await axios.post('/api/v1/jobs/collect', {
        device_filter: 'highend'
      })
      
      const jobId = response.data.id
      const wsUrl = API_BASE.replace('http', 'ws')
      const ws = new WebSocket(`${wsUrl}/ws/${jobId}`)
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        setProgress(data.message)
        if (data.message === 'Collection completed' || data.message.startsWith('Collection failed')) {
            ws.close()
        }
      }
      
      ws.onclose = () => {
        const endTime = Date.now()
        const duration = ((endTime - startTime) / 1000).toFixed(2)
        setCollectionTime(duration)
        setLoading(false)
        loadMetric()
        setTimeout(() => setProgress(null), 2500)
      }
      
      ws.onerror = () => {
        setLoading(false)
        setProgress('Connection error')
      }
      
    } catch (error) {
      setLoading(false)
      setProgress(`Error: ${error.message}`)
    }
  }

  const getHealthStatus = () => {
    if (!metric || !metric.junos_version) return { status: 'unknown', label: 'OFFLINE', color: '#9e9e9e' }
    
    const cpu = metric.cpu_usage || 0
    const mem = metric.memory_usage || 0
    
    if (cpu > 80 || mem > 80 || metric.has_core_dumps) {
      return { status: 'critical', label: 'CRITICAL', color: '#ff4b4b' }
    }
    if (cpu > 60 || mem > 60) {
      return { status: 'warning', label: 'WARNING', color: '#fca130' }
    }
    return { status: 'healthy', label: 'OPTIMAL', color: '#00e676' }
  }

  const formatNumber = (num) => {
    if (num === null || num === undefined) return 'N/A'
    return num.toLocaleString()
  }

  const formatTime = (date) => {
    if (!date) return 'Never'
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const health = getHealthStatus()

  return (
    <div className="app">
      <div className="background-shapes">
        <div className="shape shape-1"></div>
        <div className="shape shape-2"></div>
        <div className="shape shape-3"></div>
      </div>

      <header className="glass-header slide-down">
        <div className="header-content">
          <div className="brand">
            <div className="logo-icon">📡</div>
            <div>
              <h1>LONGEVITY <span>V2</span></h1>
              <p>Real-Time Network Telemetry</p>
            </div>
          </div>
          <div className="header-actions">
            <label className="toggle-switch">
              <input 
                type="checkbox" 
                checked={autoRefresh} 
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
              <span className="slider"></span>
              <span className="toggle-label">Live Monitor</span>
            </label>
            <button onClick={handleRefresh} disabled={loading} className={`refresh-btn ${loading ? 'pulsing' : ''}`}>
              {loading ? 'SYNCING...' : 'REFRESH NOW'}
            </button>
          </div>
        </div>
      </header>

      {progress && (
        <div className="floating-progress fade-in">
          <div className="spinner-ring"></div>
          <span className="progress-text">{progress}</span>
        </div>
      )}

      <main className="dashboard-container">
        <div className="device-hero glass-card slide-up stagger-1">
          <div className="device-identity">
            <h2>snpsrx4100c</h2>
            <span className="device-badge">SRX4200 Firewall</span>
          </div>
          <div className={`status-pill glow-${health.status}`}>
            <div className="pulse-dot"></div>
            {health.label}
          </div>
        </div>

        {!metric ? (
          <div className="empty-state glass-card slide-up stagger-2">
            <div className="empty-icon float-anim">⚡</div>
            <h3>Waiting for Telemetry</h3>
            <p>Click "Refresh Now" to instantaneously poll live metrics.</p>
          </div>
        ) : (
          <>
            <div className="metrics-grid">
              {/* System Info */}
              <div className="metric-card glass-card info-card span-2 slide-up stagger-2">
                <div className="card-top">
                  <h3>System Identity</h3>
                  <div className="card-icon">💻</div>
                </div>
                <div className="info-grid">
                  <Tooltip text="The unique network name assigned to this firewall on the network.">
                    <div className="info-block">
                      <span className="info-title">Hostname</span>
                      <span className="info-value host-gradient">{metric.hostname}</span>
                    </div>
                  </Tooltip>
                  <Tooltip text="The physical hardware chassis model of the device.">
                    <div className="info-block">
                      <span className="info-title">Model</span>
                      <span className="info-value">{metric.model || 'N/A'}</span>
                    </div>
                  </Tooltip>
                  <Tooltip text="The version of the Junos operating system currently running.">
                    <div className="info-block">
                      <span className="info-title">Firmware</span>
                      <span className="info-value junos-text">{metric.junos_version || 'N/A'}</span>
                    </div>
                  </Tooltip>
                  <Tooltip text="The control board unit managing the chassis operations.">
                    <div className="info-block">
                      <span className="info-title">Routing Engine</span>
                      <span className="info-value">{metric.routing_engine || 'N/A'}</span>
                    </div>
                  </Tooltip>
                </div>
              </div>

              {/* CPU */}
              <div className="metric-card glass-card visual-card slide-up stagger-3">
                <div className="card-top">
                  <Tooltip text="Percentage of processor capacity used. High usage slows down network traffic and should be monitored.">
                    <h3 className="hoverable-title">CPU Utilization <span className="info-icon">ⓘ</span></h3>
                  </Tooltip>
                </div>
                <div className="radial-metric">
                  <div className={`radial-progress stroke-${metric.cpu_usage > 80 ? 'critical' : metric.cpu_usage > 60 ? 'warning' : 'healthy'}`} style={{ '--progress': metric.cpu_usage || 0 }}>
                    <div className="radial-inner">
                      <span className="radial-value">{metric.cpu_usage || 0}</span>
                      <span className="radial-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Memory */}
              <div className="metric-card glass-card visual-card slide-up stagger-4">
                <div className="card-top">
                  <Tooltip text="Percentage of Random Access Memory (RAM) actively used by system processes.">
                    <h3 className="hoverable-title">Memory Allocation <span className="info-icon">ⓘ</span></h3>
                  </Tooltip>
                </div>
                <div className="radial-metric">
                  <div className={`radial-progress stroke-${metric.memory_usage > 80 ? 'critical' : metric.memory_usage > 60 ? 'warning' : 'healthy'}`} style={{ '--progress': metric.memory_usage || 0 }}>
                    <div className="radial-inner">
                      <span className="radial-value">{metric.memory_usage || 0}</span>
                      <span className="radial-unit">%</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Sessions Grid */}
              <div className="metric-card glass-card visual-card ds-card slide-up stagger-5">
                <div className="card-top">
                  <Tooltip text="Total active user traffic connections passing through the firewall data plane right now. Represents the actual network load.">
                    <h3 className="hoverable-title">Active Flow Sessions <span className="info-icon">ⓘ</span></h3>
                  </Tooltip>
                </div>
                <div className="big-stat">
                  <span className="stat-number glow-num">{formatNumber(metric.flow_session_current)}</span>
                  <span className="stat-trend live-pulse">● Live Traffic</span>
                </div>
              </div>

              <div className="metric-card glass-card visual-card ds-card slide-up stagger-6">
                <div className="card-top">
                  <Tooltip text="Active internal connections managing routing protocols and device configuration.">
                    <h3 className="hoverable-title">Control Plane Sessions <span className="info-icon">ⓘ</span></h3>
                  </Tooltip>
                </div>
                <div className="big-stat">
                  <span className="stat-number">{formatNumber(metric.cp_session_current)}</span>
                  <span className="stat-trend stable">Management</span>
                </div>
              </div>

              <div className="metric-card glass-card visual-card status-card slide-up stagger-7">
                <div className="card-top">
                  <Tooltip text="Crash log files. If detected, a software process recently crashed requiring engineering investigation.">
                    <h3 className="hoverable-title">System Core Dumps <span className="info-icon">ⓘ</span></h3>
                  </Tooltip>
                </div>
                <div className={`status-block ${metric.has_core_dumps ? 'danger' : 'safe'}`}>
                  <div className={`status-icon ${metric.has_core_dumps ? 'shake' : ''}`}>{metric.has_core_dumps ? '⚠️' : '🛡️'}</div>
                  <div className="status-text">{metric.has_core_dumps ? 'CRASH DETECTED' : 'SYSTEM STABLE'}</div>
                </div>
              </div>

              <div className="metric-card glass-card visual-card ds-card slide-up stagger-8">
                <div className="card-top">
                  <Tooltip text="Global Shared Memory usage. If too high, the device cannot allocate resources for new connections and may drop traffic.">
                    <h3 className="hoverable-title">Global SHM Usage <span className="info-icon">ⓘ</span></h3>
                  </Tooltip>
                </div>
                <div className="big-stat split-stat">
                  <span className="stat-number">{metric.global_data_shm_percent || 0}<span className="percent">%</span></span>
                  <div className="progress-bar-flat">
                    <div className={`progress-fill bg-${(metric.global_data_shm_percent || 0) > 70 ? 'critical' : 'healthy'}`} style={{ width: `${metric.global_data_shm_percent || 0}%` }}></div>
                  </div>
                </div>
              </div>
            </div>

            <div className="glass-footer slide-up stagger-9">
              <div className="footer-stat">
                <span className="footer-label">Last Synchronization</span>
                <span className="footer-value">SYNC: {lastUpdated ? formatTime(lastUpdated) : 'Never'}</span>
              </div>
              
              {collectionTime && (
                <div className="footer-stat">
                  <span className="footer-label">Optimization Latency</span>
                  <span className="footer-value glow-green">{collectionTime}s ⚡</span>
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  )
}

export default App
