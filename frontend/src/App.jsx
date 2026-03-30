import { useState, useEffect, useMemo } from 'react'
import axios from 'axios'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts'
import './App.css'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
axios.defaults.baseURL = API_BASE

const DEVICES = [
  { name: "snpsrx4300a", vm: "snpsrx4300a.englab.juniper.net", type: "highend" },
  { name: "snpsrx1600a", vm: "snpsrx1600a.englab.juniper.net", type: "highend" },
  { name: "snpsrx4300b", vm: "snpsrx4300b.englab.juniper.net", type: "highend" },
  { name: "snpsrx1600b", vm: "snpsrx1600b.englab.juniper.net", type: "highend" },
  { name: "esst-srv66-http01", vm: "esst-srv66-http01.englab.juniper.net", type: "vsrx" },
  { name: "snpsrx4100c", vm: "snpsrx4100c.englab.juniper.net", type: "highend" },
  { name: "snpsrx380e", vm: "snpsrx380e.englab.juniper.net", type: "branch" },
  { name: "esst-srv61-http01", vm: "esst-srv61-http01.englab.juniper.net", type: "vsrx" },
  { name: "snpsrx1500aa", vm: "snpsrx1500aa.englab.juniper.net", type: "highend" },
  { name: "snpsrx4600j", vm: "snpsrx4600j.englab.juniper.net", type: "highend" },
  { name: "snpsrx4120c", vm: "snpsrx4120c.englab.juniper.net", type: "highend" },
  { name: "snpsrx345d", vm: "snpsrx345d.englab.juniper.net", type: "branch" },
  { name: "snpsrx340k", vm: "snpsrx340k.englab.juniper.net", type: "branch" },
  { name: "snpsrx300y", vm: "snpsrx300y.englab.juniper.net", type: "branch" },
  { name: "snpsrx5600q", vm: "snpsrx5600q.englab.juniper.net", type: "spc3" }
];

const DEVICE_TYPES = ['ALL', ...new Set(DEVICES.map(d => d.type.toUpperCase()))];

function Tooltip({ text, children }) {
  return (
    <div className="tooltip-container">
      {children}
      <div className="tooltip-text">{text}</div>
    </div>
  )
}

function App() {
  const [deviceFilter, setDeviceFilter] = useState('ALL')
  const [metric, setMetric] = useState(null)
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(null)
  const [collectionTime, setCollectionTime] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [selectedDevice, setSelectedDevice] = useState(null)
  const [allMetrics, setAllMetrics] = useState([])
  const [historyData, setHistoryData] = useState([])
  const [viewMode, setViewMode] = useState('grid')

  const filteredAndSortedDevices = useMemo(() => {
    return DEVICES.filter(d => deviceFilter === 'ALL' || d.type.toUpperCase() === deviceFilter)
      .sort((a, b) => b.name.localeCompare(a.name, undefined, { numeric: true, sensitivity: 'base' }))
  }, [deviceFilter])

  const loadHistoricalMetrics = async (deviceId) => {
    try {
      const res = await axios.get(`/api/v1/metrics/device/${deviceId}`)
      const formatted = (res.data || []).map(d => {
        // Backend returns UTC timestamps without 'Z' suffix, so we need to append it
        const dt = new Date(d.timestamp + 'Z');
        return {
          ...d,
          time: dt.toLocaleTimeString('en-US', {hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata', timeZoneName: 'short'}),
          fullDateTime: dt.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata', timeZoneName: 'short' })
        };
      })
      setHistoryData(formatted.slice(0, 20).reverse())
    } catch(e) {
      console.error('Failed to load historical metrics:', e)
    }
  }

  const loadAllMetrics = async () => {
    try {
      const response = await axios.get('/api/v1/metrics/latest')
      setAllMetrics(response.data || [])
    } catch (error) {
      console.error('Failed to load all metrics:', error)
    }
  }

  useEffect(() => {
    loadAllMetrics()
  }, [])

  useEffect(() => {
    if (selectedDevice) {
      loadMetric()
    } else {
      setMetric(null)
      setProgress(null)
      setCollectionTime(null)
    }
  }, [selectedDevice])

  useEffect(() => {
    if (autoRefresh && selectedDevice) {
      const interval = setInterval(() => {
        handleRefresh()
      }, 60000)
      return () => clearInterval(interval)
    }
  }, [autoRefresh, selectedDevice])

  const loadMetric = async () => {
    if (!selectedDevice) return;
    try {
      const response = await axios.get('/api/v1/metrics/latest')
      const data = response.data || []
      const device = data.find(d => d.device_name === selectedDevice.name || d.hostname.includes(selectedDevice.name))
      setMetric(device || null)
      if (device && device.device_id) {
        loadHistoricalMetrics(device.device_id)
      }
      setLastUpdated(new Date())
    } catch (error) {
      console.error('Failed to load metrics:', error)
      setMetric(null)
    }
  }

  const handleRefresh = async () => {
    if (!selectedDevice) return;
    setLoading(true)
    setProgress('Establishing High-Speed Channel...')
    const startTime = Date.now()
    
    try {
      const response = await axios.post('/api/v1/jobs/collect', {
        device_name: selectedDevice.name  // Send specific device name
      })
      
      const jobId = response.data.id
      const wsUrl = API_BASE.replace('http', 'ws')
      const ws = new WebSocket(`${wsUrl}/ws/${jobId}`)
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        setProgress(data.message)
        if (data.message.includes('completed') || data.message.includes('failed') || data.message.includes('Failed')) {
            ws.close()
        }
      }
      
      ws.onclose = () => {
        const endTime = Date.now()
        const duration = ((endTime - startTime) / 1000).toFixed(2)
        setCollectionTime(duration)
        setLoading(false)
        // Reload metrics & graph after collection
        setTimeout(() => {
          loadMetric()
          loadAllMetrics()
        }, 500)
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

  const handleFetchFiltered = async () => {
    setLoading(true)
    setProgress(`Tracking ${deviceFilter === 'ALL' ? 'All' : deviceFilter} Network Telemetry...`)
    const startTime = Date.now()
    
    try {
      const response = await axios.post('/api/v1/jobs/collect', {
        device_filter: deviceFilter === 'ALL' ? 'all' : deviceFilter.toLowerCase()
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
        setLastUpdated(new Date())
        // Small delay to ensure DB commit has propagated before querying
        setTimeout(() => {
          loadAllMetrics()
        }, 500)
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
            {selectedDevice && (
              <button className="back-btn" onClick={() => setSelectedDevice(null)}>
                <span className="back-icon">←</span> DEVICES
              </button>
            )}
            <div className="brand" onClick={() => setSelectedDevice(null)} style={{cursor: 'pointer'}} title="Return to Devices">
              <div className="logo-icon">📡</div>
              <div>
                <h1>LONGEVITY <span>V2</span></h1>
                <p>Real-Time Network Telemetry</p>
              </div>
            </div>
          </div>
          {selectedDevice && (
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
          )}
        </div>
      </header>

      {progress && (
        <div className="floating-progress fade-in">
          <div className="spinner-ring"></div>
          <span className="progress-text">{progress}</span>
        </div>
      )}

      <main className="dashboard-container">
        {!selectedDevice ? (
          <>
            <div className="filter-container fade-in">
              <div className="filter-group">
                <label htmlFor="device-filter">Device Type</label>
                <select 
                  id="device-filter" 
                  value={deviceFilter} 
                  onChange={(e) => setDeviceFilter(e.target.value)}
                  className="device-filter-select"
                >
                  {DEVICE_TYPES.map(type => (
                    <option key={type} value={type}>{type === 'ALL' ? 'ALL DEVICES' : type}</option>
                  ))}
                </select>
              </div>
              <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                <div className="view-toggle">
                  <button className={viewMode === 'grid' ? 'active' : ''} onClick={() => setViewMode('grid')}>▦ Cards</button>
                  <button className={viewMode === 'table' ? 'active' : ''} onClick={() => setViewMode('table')}>☰ List</button>
                </div>
                <button 
                  className={`refresh-btn ${loading ? 'pulsing' : ''}`} 
                  onClick={handleFetchFiltered}
                  disabled={loading}
                >
                  {loading ? 'SYNCING...' : `FETCH ${deviceFilter === 'ALL' ? 'ALL' : deviceFilter} METRICS`}
                </button>
              </div>
            </div>
            {viewMode === 'grid' ? (
              <div className="landing-grid fade-in">
                {filteredAndSortedDevices.map((d, index) => (
                  <div 
                  key={d.name} 
                  className={`device-card glass-card slide-up type-${d.type}`}
                  style={{ animationDelay: `${index * 0.05}s` }}
                  onClick={() => setSelectedDevice(d)}
                >
                  <div className={`card-top-accent accent-${d.type}`}></div>
                  <div className="device-card-header">
                    <h3>{d.name}</h3>
                    <span className={`device-type-badge type-${d.type}`}>{d.type.toUpperCase()}</span>
                  </div>
                  <div className="device-card-body">
                    {(() => {
                      const dMetric = allMetrics.find(m => m.device_name === d.name || m.hostname?.includes(d.name))
                      if (dMetric) {
                        return (
                          <div className="mini-metrics-grid">
                            <div className="m-stat"><span className="m-lbl">CPU</span><span className={`m-val ${dMetric.cpu_usage > 80 ? 'text-red' : ''}`}>{dMetric.cpu_usage || 0}%</span></div>
                            <div className="m-stat"><span className="m-lbl">MEM</span><span className={`m-val ${dMetric.memory_usage > 80 ? 'text-red' : ''}`}>{dMetric.memory_usage || 0}%</span></div>
                            <div className="m-stat"><span className="m-lbl">SHM</span><span className={`m-val ${(dMetric.global_data_shm_percent || 0) > 70 ? 'text-red' : ''}`}>{dMetric.global_data_shm_percent || 0}%</span></div>
                            <div className="m-stat"><span className="m-lbl">CORES</span><span className={`m-val ${dMetric.has_core_dumps ? 'text-red' : ''}`}>{dMetric.has_core_dumps ? 'YES' : 'NO'}</span></div>
                          </div>
                        )
                      }
                      return (
                        <div className="device-vm">
                          <span className="vm-icon">🌐</span>
                          <span>{d.vm}</span>
                        </div>
                      )
                    })()}
                  </div>
                  <div className="device-card-footer">
                    <span className="connect-text">View Telemetry →</span>
                  </div>
                </div>
                ))}
              </div>
            ) : (
              <div className="device-table-container fade-in slide-up">
                <table className="device-table">
                  <thead>
                    <tr>
                      <th>Device Name</th>
                      <th>Type</th>
                      <th>CPU</th>
                      <th>Memory</th>
                      <th>SHM</th>
                      <th>Cores</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredAndSortedDevices.map((d, index) => {
                        const dMetric = allMetrics.find(m => m.device_name === d.name || m.hostname?.includes(d.name))
                        return (
                          <tr key={d.name} onClick={() => setSelectedDevice(d)} style={{ animationDelay: `${index * 0.03}s` }} className="slide-up">
                            <td className="font-bold">{d.name}</td>
                            <td><span className={`device-type-badge type-${d.type}`}>{d.type.toUpperCase()}</span></td>
                            {dMetric ? (
                              <>
                                <td className={dMetric.cpu_usage > 80 ? 'text-red font-bold' : ''}>{dMetric.cpu_usage || 0}%</td>
                                <td className={dMetric.memory_usage > 80 ? 'text-red font-bold' : ''}>{dMetric.memory_usage || 0}%</td>
                                <td className={(dMetric.global_data_shm_percent || 0) > 70 ? 'text-red font-bold' : ''}>{dMetric.global_data_shm_percent || 0}%</td>
                                <td className={dMetric.has_core_dumps ? 'text-red font-bold' : ''}>{dMetric.has_core_dumps ? 'YES' : 'NO'}</td>
                              </>
                            ) : (
                              <td colSpan="4" className="text-gray italic text-center">No telemetry loaded</td>
                            )}
                            <td className="action-cell">View Telemetry →</td>
                          </tr>
                        )
                      })}
                  </tbody>
                </table>
              </div>
            )}
          </>
        ) : (
          <>
            <div className="device-hero glass-card slide-up stagger-1">
              <div className="device-identity">
                <h2>{selectedDevice.name}</h2>
                <span className="device-badge">{selectedDevice.type.toUpperCase()} Firewall</span>
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
                <p>Click "Refresh Now" to instantaneously poll live metrics for {selectedDevice.name}.</p>
              </div>
            ) : (
          <>
            <div className="metrics-grid">
              {/* History Graph */}
              <div className="metric-card glass-card info-card span-2 slide-up stagger-2" style={{ padding: '1.2rem' }}>
                <div className="card-top" style={{ marginBottom: '0.5rem' }}>
                  <h3>Telemetry History</h3>
                  <div className="card-icon">📈</div>
                </div>
                <div style={{ width: '100%', height: '220px' }}>
                  {historyData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={historyData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <defs>
                          <linearGradient id="colorCpu" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#8DC63F" stopOpacity={0.3}/>
                            <stop offset="95%" stopColor="#8DC63F" stopOpacity={0}/>
                          </linearGradient>
                          <linearGradient id="colorMem" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.3}/>
                            <stop offset="95%" stopColor="#38bdf8" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <XAxis dataKey="time" tick={{fontSize: 10, fill: '#6b7280'}} tickLine={false} axisLine={false} />
                        <YAxis tick={{fontSize: 10, fill: '#6b7280'}} tickLine={false} axisLine={false} domain={[0, 100]} />
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                        <RechartsTooltip 
                          labelFormatter={(label, payload) => {
                            if (payload && payload.length > 0) {
                              return payload[0].payload.fullDateTime || label;
                            }
                            return label;
                          }}
                          contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}
                          labelStyle={{ fontWeight: 'bold', color: '#111827', marginBottom: '5px' }}
                        />
                        <Area type="monotone" name="CPU %" dataKey="cpu_usage" stroke="#8DC63F" strokeWidth={2} fillOpacity={1} fill="url(#colorCpu)" />
                        <Area type="monotone" name="Memory %" dataKey="memory_usage" stroke="#38bdf8" strokeWidth={2} fillOpacity={1} fill="url(#colorMem)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: '#9ca3af' }}>
                      Insufficient historical data
                    </div>
                  )}
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
          </>
        )}
      </main>
    </div>
  )
}

export default App
