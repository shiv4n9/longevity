import { useState, useEffect, useMemo } from 'react'
import axios from 'axios'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer } from 'recharts'
import './App.css'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
axios.defaults.baseURL = API_BASE

const DEVICE_TYPES = ['ALL', 'HIGHEND', 'BRANCH', 'VSRX', 'SPC3', 'NFX'];

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
  const [platformFilter, setPlatformFilter] = useState('ALL')
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
  const [selectedDevices, setSelectedDevices] = useState(new Set())
  const [selectionMode, setSelectionMode] = useState(false)
  const [showCoreDumpModal, setShowCoreDumpModal] = useState(false)
  const [historyTimeRange, setHistoryTimeRange] = useState(1) // days
  const [autoMonitoring, setAutoMonitoring] = useState(false)
  const [showAddDeviceModal, setShowAddDeviceModal] = useState(false)
  const [newDevice, setNewDevice] = useState({
    name: '',
    hostname: '',
    device_type: 'highend',
    routing: 'direct'
  })
  const [devices, setDevices] = useState([])

  const filteredAndSortedDevices = useMemo(() => {
    // First filter by device type
    let filtered = devices.filter(d => deviceFilter === 'ALL' || d.type.toUpperCase() === deviceFilter)
    
    // Enrich devices with platform info from metrics
    const enrichedDevices = filtered.map(device => {
      const metric = allMetrics.find(m => m.device_name === device.name)
      // Use platform from metrics if available, otherwise fallback to device name
      const platform = metric?.platform || device.name.toUpperCase()
      const isActive = metric && metric.cpu_usage !== null && metric.cpu_usage !== undefined
      return { ...device, platform, metric, isActive }
    })
    
    // Filter by platform if selected
    const platformFiltered = platformFilter === 'ALL' 
      ? enrichedDevices 
      : enrichedDevices.filter(d => d.platform === platformFilter)
    
    // Sort by platform name, then by device name
    return platformFiltered.sort((a, b) => {
      const platformCompare = a.platform.localeCompare(b.platform, undefined, { numeric: true, sensitivity: 'base' })
      if (platformCompare !== 0) return platformCompare
      return a.name.localeCompare(b.name)
    })
  }, [deviceFilter, platformFilter, allMetrics, devices])

  // Get unique platforms from filtered devices
  const availablePlatforms = useMemo(() => {
    const filtered = devices.filter(d => deviceFilter === 'ALL' || d.type.toUpperCase() === deviceFilter)
    const enriched = filtered.map(device => {
      const metric = allMetrics.find(m => m.device_name === device.name)
      return metric?.platform || device.name.toUpperCase()
    })
    const unique = ['ALL', ...new Set(enriched)].sort((a, b) => {
      if (a === 'ALL') return -1
      if (b === 'ALL') return 1
      return a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' })
    })
    return unique
  }, [deviceFilter, allMetrics, devices])

  // Reset platform filter when device type changes
  useEffect(() => {
    setPlatformFilter('ALL')
  }, [deviceFilter])

  const loadHistoricalMetrics = async (deviceId) => {
    try {
      // Pass days parameter to backend to filter at database level
      const res = await axios.get(`/api/v1/metrics/device/${deviceId}`, {
        params: { days: historyTimeRange }
      })
      
      // Format the data
      const formatted = (res.data || []).map(d => {
        const dt = new Date(d.timestamp + 'Z');
        return {
          ...d,
          time: dt.toLocaleString('en-IN', {
            month: 'short', 
            day: 'numeric', 
            hour: '2-digit', 
            minute: '2-digit',
            timeZone: 'Asia/Kolkata'
          }),
          fullDateTime: dt.toLocaleString('en-IN', { 
            month: 'short', 
            day: 'numeric', 
            year: 'numeric',
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit',
            timeZone: 'Asia/Kolkata'
          })
        };
      })
      
      // Sort by timestamp (oldest first for the graph)
      const sorted = formatted.sort((a, b) => new Date(a.timestamp + 'Z') - new Date(b.timestamp + 'Z'))
      
      console.log(`Loaded ${sorted.length} data points for past ${historyTimeRange} day(s)`)
      setHistoryData(sorted)
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

  // Reload historical data when time range changes
  useEffect(() => {
    if (selectedDevice && metric && metric.device_id) {
      loadHistoricalMetrics(metric.device_id)
    }
  }, [historyTimeRange, selectedDevice, metric])

  useEffect(() => {
    loadAllMetrics()
    loadDevices()
    checkSchedulerStatus()
  }, [])

  // Handle URL parameters after devices are loaded
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search)
    const deviceParam = urlParams.get('device')
    const filterParam = urlParams.get('filter')
    
    if (deviceParam && devices.length > 0) {
      // Auto-select device from URL parameter
      const device = devices.find(d => d.name === deviceParam)
      if (device) {
        setSelectedDevice(device)
      }
    }
    
    if (filterParam) {
      // Auto-apply filter from URL parameter
      setDeviceFilter(filterParam.toUpperCase())
    }
  }, [devices])

  const loadDevices = async () => {
    try {
      const response = await axios.get('/api/v1/devices/')
      setDevices(response.data.map(d => ({
        name: d.name,
        vm: d.hostname,
        type: d.device_type
      })))
    } catch (error) {
      console.error('Failed to load devices:', error)
    }
  }

  const checkSchedulerStatus = async () => {
    try {
      const response = await axios.get('/api/v1/scheduler/status')
      setAutoMonitoring(response.data.running)
    } catch (error) {
      console.error('Failed to check scheduler status:', error)
    }
  }

  const toggleAutoMonitoring = async () => {
    try {
      if (autoMonitoring) {
        await axios.post('/api/v1/scheduler/stop')
        setAutoMonitoring(false)
      } else {
        await axios.post('/api/v1/scheduler/start')
        setAutoMonitoring(true)
      }
    } catch (error) {
      console.error('Failed to toggle auto-monitoring:', error)
    }
  }

  const handleAddDevice = async () => {
    try {
      await axios.post('/api/v1/devices/', newDevice)
      setShowAddDeviceModal(false)
      setNewDevice({ name: '', hostname: '', device_type: 'highend', routing: 'direct' })
      // Reload devices and metrics to show the new device
      await loadDevices()
      loadAllMetrics()
      alert('Device added successfully!')
    } catch (error) {
      console.error('Failed to add device:', error)
      alert(error.response?.data?.detail || 'Failed to add device')
    }
  }

  useEffect(() => {
    if (selectedDevice) {
      loadMetric()
    } else {
      setMetric(null)
      setProgress(null)
      setCollectionTime(null)
    }
  }, [selectedDevice])

  // Reload metric when allMetrics updates (after collection) and we're viewing a device
  useEffect(() => {
    if (selectedDevice && allMetrics.length > 0) {
      const updatedMetric = allMetrics.find(d => d.device_name === selectedDevice.name || d.hostname?.includes(selectedDevice.name))
      if (updatedMetric) {
        setMetric(updatedMetric)
        if (updatedMetric.device_id) {
          loadHistoricalMetrics(updatedMetric.device_id)
        }
      }
    }
  }, [allMetrics])

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

  const toggleDeviceSelection = (deviceName) => {
    setSelectedDevices(prev => {
      const newSet = new Set(prev)
      if (newSet.has(deviceName)) {
        newSet.delete(deviceName)
      } else {
        newSet.add(deviceName)
      }
      return newSet
    })
  }

  const selectAllDevices = () => {
    const allDeviceNames = filteredAndSortedDevices.map(d => d.name)
    setSelectedDevices(new Set(allDeviceNames))
  }

  const clearSelection = () => {
    setSelectedDevices(new Set())
  }

  const handleFetchSelected = async () => {
    if (selectedDevices.size === 0) {
      alert('Please select at least one device')
      return
    }

    setLoading(true)
    const deviceNames = Array.from(selectedDevices)
    setProgress(`Collecting metrics from ${deviceNames.length} selected device(s)...`)
    const startTime = Date.now()
    
    try {
      // Send all selected devices in a single request
      const response = await axios.post('/api/v1/jobs/collect', {
        device_names: deviceNames  // Send array of device names
      })
      
      const jobId = response.data.id
      const wsUrl = API_BASE.replace('http', 'ws')
      const ws = new WebSocket(`${wsUrl}/ws/${jobId}`)
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        setProgress(data.message)
        if (data.message.includes('completed') || data.message.includes('failed')) {
          ws.close()
        }
      }
      
      ws.onclose = () => {
        const endTime = Date.now()
        const duration = ((endTime - startTime) / 1000).toFixed(2)
        setCollectionTime(duration)
        setLoading(false)
        setProgress(`Completed ${deviceNames.length} device(s) in ${duration}s`)
        
        // Reload metrics
        setTimeout(() => {
          loadAllMetrics()
          setProgress(null)
          setSelectionMode(false)
          clearSelection()
        }, 2000)
      }
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setLoading(false)
        setProgress('Connection error')
        setTimeout(() => setProgress(null), 3000)
      }
      
    } catch (error) {
      console.error('Collection error:', error)
      setProgress(`Error: ${error.message}`)
      setLoading(false)
      setTimeout(() => setProgress(null), 3000)
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

  const parseCoreDumps = (output) => {
    console.log('[Core Dumps] Raw output:', output);
    
    if (!output) {
      console.log('[Core Dumps] No output provided');
      return [];
    }
    
    const dumps = [];
    const lines = output.split('\n');
    let currentPath = '/var/crash'; // default path
    
    console.log('[Core Dumps] Processing', lines.length, 'lines');
    
    for (const line of lines) {
      // Skip empty lines and non-file lines
      if (!line.trim() || line.includes('No such file') || line.includes('total blocks:') || 
          line.includes('total files:') || line.includes('show system') || 
          line.match(/^[>#]/)) {
        continue;
      }
      
      // Check if line is a directory path
      if (line.trim().endsWith(':')) {
        currentPath = line.trim().replace(':', '');
        console.log('[Core Dumps] Found path:', currentPath);
        continue;
      }
      
      // Try to match the line with the file listing pattern
      // Match various formats:
      // -rw-r--r--  1 root  wheel  962077195 Mar 31 04:20 core-srxpfe.tgz
      // -rw-------  1 root  root   4261684 Apr 16 19:49 /var/core/re0/named.re.re0.7982.tar.gz
      // -rw-xr-xr-x  1 root  wheel  394231808 Apr 15 00:29 /var/crash/vmcore.0
      // lrwxr-xr-x  1 root  wheel  8 Apr 18 00:29 /var/crash/vmcore.last0 -> vmcore.0
      
      // Pattern: permissions user group size date time filename
      const match = line.match(/^([l-][\w-]+)\s+\d+\s+\S+\s+\S+\s+(\d+)\s+(\S+\s+\d+\s+[\d:]+)\s+(.+?)(\s*->\s*.+)?$/);
      
      if (match) {
        const [, permissions, bytes, datetime, filepath, symlink] = match;
        
        console.log('[Core Dumps] Matched line:', { permissions, bytes, datetime, filepath });
        
        // Extract just the filename from the full path
        const filename = filepath.split('/').pop();
        
        // Skip if it's a symlink (starts with 'l')
        if (permissions.startsWith('l')) {
          console.log('[Core Dumps] Skipping symlink:', filename);
          continue;
        }
        
        // Only include files that look like core dumps
        const lowerFilename = filename.toLowerCase();
        if (!lowerFilename.includes('core') && !lowerFilename.includes('vmcore') && 
            !lowerFilename.includes('named') && !lowerFilename.includes('srxpfe') &&
            !lowerFilename.includes('rpd') && !lowerFilename.includes('kernel') &&
            !lowerFilename.includes('chassisd')) {
          console.log('[Core Dumps] Skipping non-core file:', filename);
          continue;
        }
        
        // Determine type based on filename
        let type = 'System Core Dump';
        let color = 'red';
        
        if (lowerFilename.includes('srxpfe')) {
          type = 'Packet Forwarding Engine';
          color = 'red';
        } else if (lowerFilename.includes('rpd')) {
          type = 'Routing Protocol Daemon';
          color = 'orange';
        } else if (lowerFilename.includes('kernel') || lowerFilename.includes('vmcore')) {
          type = 'Kernel Core';
          color = 'purple';
        } else if (lowerFilename.includes('chassisd')) {
          type = 'Chassis Daemon';
          color = 'blue';
        } else if (lowerFilename.includes('named')) {
          type = 'Named Daemon';
          color = 'orange';
        }
        
        // Use the full path if it starts with /, otherwise construct it
        const fullPath = filepath.startsWith('/') ? filepath : `${currentPath}/${filename}`;
        
        const dump = { filename, path: fullPath, datetime, type, color, bytes: parseInt(bytes) };
        console.log('[Core Dumps] Adding dump:', dump);
        dumps.push(dump);
      }
    }
    
    console.log('[Core Dumps] Total dumps found:', dumps.length);
    return dumps;
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
          <div className="header-actions">
            {!selectedDevice && (
              <label className="toggle-switch">
                <input 
                  type="checkbox" 
                  checked={autoMonitoring} 
                  onChange={toggleAutoMonitoring}
                />
                <span className="slider"></span>
                <span className="toggle-label">Auto-Monitor (10min)</span>
              </label>
            )}
            {selectedDevice && (
              <>
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
              </>
            )}
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
        {!selectedDevice ? (
          <>
            <div className="filter-container fade-in">
              <div className="filter-row">
                <div className="filter-tabs">
                  <div className="filter-tab">
                    <span className="filter-tab-label">Device Type</span>
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
                  <div className="filter-tab">
                    <span className="filter-tab-label">Platform</span>
                    <select 
                      id="platform-filter" 
                      value={platformFilter} 
                      onChange={(e) => setPlatformFilter(e.target.value)}
                      className="device-filter-select"
                    >
                      {availablePlatforms.map(platform => (
                        <option key={platform} value={platform}>
                          {platform === 'ALL' ? 'ALL PLATFORMS' : platform}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="view-toggle">
                  <span className="view-toggle-label">View</span>
                  <div className="view-toggle-buttons">
                    <button className={viewMode === 'grid' ? 'active' : ''} onClick={() => setViewMode('grid')}>▦ Cards</button>
                    <button className={viewMode === 'table' ? 'active' : ''} onClick={() => setViewMode('table')}>☰ List</button>
                  </div>
                </div>
              </div>
              
              <div className="filter-row">
                <div className="action-buttons">
                  {!selectionMode ? (
                    <>
                      <button 
                        className="selection-mode-btn"
                        onClick={() => setSelectionMode(true)}
                      >
                        ☑ Select Devices
                      </button>
                      <button 
                        className="selection-mode-btn"
                        onClick={() => setShowAddDeviceModal(true)}
                        style={{background: '#00e676'}}
                      >
                        ➕ Add Device
                      </button>
                    </>
                  ) : (
                    <>
                      <button 
                        className="select-all-btn"
                        onClick={selectAllDevices}
                      >
                        Select All ({filteredAndSortedDevices.length})
                      </button>
                      <button 
                        className="clear-selection-btn"
                        onClick={clearSelection}
                      >
                        Clear
                      </button>
                      <button 
                        className="cancel-selection-btn"
                        onClick={() => {
                          setSelectionMode(false)
                          clearSelection()
                        }}
                      >
                        Cancel
                      </button>
                    </>
                  )}
                </div>
                <div className="action-buttons">
                  {!selectionMode ? (
                    <button 
                      className={`refresh-btn ${loading ? 'pulsing' : ''}`} 
                      onClick={handleFetchFiltered}
                      disabled={loading}
                    >
                      {loading ? 'SYNCING...' : `FETCH ${deviceFilter === 'ALL' ? 'ALL' : deviceFilter} METRICS`}
                    </button>
                  ) : (
                    <button 
                      className={`refresh-btn ${loading ? 'pulsing' : ''}`}
                      onClick={handleFetchSelected}
                      disabled={loading || selectedDevices.size === 0}
                    >
                      {loading ? 'SYNCING...' : `FETCH SELECTED (${selectedDevices.size})`}
                    </button>
                  )}
                </div>
              </div>
            </div>
            {viewMode === 'grid' ? (
              <div className="landing-grid fade-in">
                {filteredAndSortedDevices.map((d, index) => (
                  <div 
                  key={d.name} 
                  className={`device-card glass-card slide-up type-${d.type} ${selectionMode ? 'selection-mode' : ''} ${selectedDevices.has(d.name) ? 'selected' : ''}`}
                  style={{ animationDelay: `${index * 0.05}s` }}
                  onClick={() => selectionMode ? toggleDeviceSelection(d.name) : setSelectedDevice(d)}
                >
                  {selectionMode && (
                    <div className="device-checkbox">
                      <input 
                        type="checkbox" 
                        checked={selectedDevices.has(d.name)}
                        onChange={() => toggleDeviceSelection(d.name)}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </div>
                  )}
                  <div className={`card-top-accent accent-${d.type}`}></div>
                  <div className="device-card-header">
                    <h3>{d.platform}</h3>
                    <span className={`device-type-badge type-${d.type}`}>{d.type.toUpperCase()}</span>
                  </div>
                  <div className="device-card-subtitle">
                    <span className={`active-device-label ${d.isActive ? 'active' : 'inactive'}`}>
                      {d.name} {d.isActive ? '✓' : '○'}
                    </span>
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
                      {selectionMode && <th style={{width: '50px'}}>Select</th>}
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
                          <tr 
                            key={d.name} 
                            onClick={() => selectionMode ? toggleDeviceSelection(d.name) : setSelectedDevice(d)} 
                            style={{ animationDelay: `${index * 0.03}s` }} 
                            className={`slide-up ${selectionMode && selectedDevices.has(d.name) ? 'table-row-selected' : ''}`}
                          >
                            {selectionMode && (
                              <td onClick={(e) => e.stopPropagation()}>
                                <input 
                                  type="checkbox" 
                                  checked={selectedDevices.has(d.name)}
                                  onChange={() => toggleDeviceSelection(d.name)}
                                  className="table-checkbox"
                                />
                              </td>
                            )}
                            <td className="font-bold">
                              <div>{d.platform}</div>
                              <div style={{fontSize: '0.75rem', color: '#888', marginTop: '0.25rem'}}>{d.name}</div>
                            </td>
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
                            <td className="action-cell">{selectionMode ? 'Select' : 'View Telemetry →'}</td>
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
                <h2>{selectedDevice.platform || metric?.platform || selectedDevice.name.toUpperCase()}</h2>
                <div className="device-subtitle-row">
                  <span className="active-device-text">Active Device: {selectedDevice.name}</span>
                  <span className="device-badge">{selectedDevice.type.toUpperCase()} Firewall</span>
                </div>
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
                <p>Click "Refresh Now" to instantaneously poll live metrics for {selectedDevice.platform || metric?.platform || selectedDevice.name} ({selectedDevice.name}).</p>
              </div>
            ) : (
          <>
            <div className="metrics-grid">
              {/* History Graph */}
              <div className="metric-card glass-card info-card span-2 slide-up stagger-2" style={{ padding: '1.2rem' }}>
                <div className="card-top" style={{ marginBottom: '0.5rem' }}>
                  <h3>Telemetry History</h3>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <select 
                      value={historyTimeRange} 
                      onChange={(e) => setHistoryTimeRange(Number(e.target.value))}
                      className="time-range-select"
                    >
                      <option value={1}>Past 24 Hours</option>
                      <option value={2}>Past 2 Days</option>
                      <option value={3}>Past 3 Days</option>
                      <option value={7}>Past Week</option>
                      <option value={14}>Past 2 Weeks</option>
                      <option value={30}>Past Month</option>
                    </select>
                    <div className="card-icon">📈</div>
                  </div>
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
                          <linearGradient id="colorShm" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3}/>
                            <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <XAxis dataKey="time" tick={{fontSize: 10, fill: '#6b7280'}} tickLine={false} axisLine={false} />
                        <YAxis tick={{fontSize: 10, fill: '#6b7280'}} tickLine={false} axisLine={false} domain={[0, 100]} />
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                        <Legend wrapperStyle={{fontSize: '12px'}} />
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
                        <Area type="monotone" name="SHM %" dataKey="global_data_shm_percent" stroke="#f59e0b" strokeWidth={2} fillOpacity={1} fill="url(#colorShm)" />
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
                  <div className="status-text">
                    {metric.has_core_dumps ? (
                      <span 
                        onClick={() => setShowCoreDumpModal(true)} 
                        style={{cursor: 'pointer', textDecoration: 'underline'}}
                        title="Click to view core dump details"
                      >
                        CORE DETECTED
                      </span>
                    ) : (
                      'SYSTEM STABLE'
                    )}
                  </div>
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
            </div>
            
            {collectionTime && (
              <div className="refresh-time-badge">
                Page Refresh: {collectionTime}s
              </div>
            )}
          </>
        )}
          </>
        )}
      </main>

      {/* Core Dump Modal */}
      {showCoreDumpModal && metric && (
        <div className="modal-overlay" onClick={() => setShowCoreDumpModal(false)}>
          <div className="dump-cards-container" onClick={(e) => e.stopPropagation()}>
            <div className="dump-header">
              <div className="dump-header-content">
                <h2>⚠️ Core Dumps Detected</h2>
                <p>{selectedDevice?.name}</p>
              </div>
              <button className="dump-close-btn" onClick={() => setShowCoreDumpModal(false)}>✕</button>
            </div>
            
            <div className="dump-cards-grid">
              {parseCoreDumps(metric.raw_data?.core_dumps_output).map((dump, index) => (
                <div key={index} className="dump-card" style={{animationDelay: `${index * 0.1}s`}}>
                  <div className={`dump-card-header dump-${dump.color}`}>
                    <span className="dump-type-badge">{dump.type}</span>
                  </div>
                  <div className="dump-card-body">
                    <div className="dump-info-row">
                      <span className="dump-label">📄 File</span>
                      <span className="dump-value dump-filename">{dump.filename}</span>
                    </div>
                    <div className="dump-info-row">
                      <span className="dump-label">📂 Path</span>
                      <span className="dump-value dump-path">{dump.path}</span>
                    </div>
                    <div className="dump-info-row">
                      <span className="dump-label">🕐 Date</span>
                      <span className="dump-value">{dump.datetime}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            
            {parseCoreDumps(metric.raw_data?.core_dumps_output).length === 0 && (
              <div className="no-dumps">
                <p>No core dump files found</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Add Device Modal */}
      {showAddDeviceModal && (
        <div className="modal-overlay" onClick={() => setShowAddDeviceModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Add New Device</h2>
            <div className="form-group">
              <label>Device Name</label>
              <input
                type="text"
                value={newDevice.name}
                onChange={(e) => setNewDevice({...newDevice, name: e.target.value})}
                placeholder="e.g., snpsrx4300a"
              />
            </div>
            <div className="form-group">
              <label>Hostname</label>
              <input
                type="text"
                value={newDevice.hostname}
                onChange={(e) => setNewDevice({...newDevice, hostname: e.target.value})}
                placeholder="e.g., snpsrx4300a.englab.juniper.net"
              />
            </div>
            <div className="form-group">
              <label>Device Type</label>
              <select
                value={newDevice.device_type}
                onChange={(e) => setNewDevice({...newDevice, device_type: e.target.value})}
              >
                <option value="highend">Highend</option>
                <option value="branch">Branch</option>
                <option value="vsrx">vSRX</option>
                <option value="spc3">SPC3</option>
                <option value="nfx">NFX</option>
              </select>
            </div>
            <div className="form-group">
              <label>Routing Mode</label>
              <select
                value={newDevice.routing}
                onChange={(e) => setNewDevice({...newDevice, routing: e.target.value})}
              >
                <option value="direct">Direct (Fastest - from esst-srv2-arm)</option>
                <option value="single-hop">Single-hop (via jump host)</option>
                <option value="double-hop">Double-hop (via jump + esst-srv2-arm)</option>
              </select>
            </div>
            <div className="modal-actions">
              <button onClick={() => setShowAddDeviceModal(false)} className="cancel-btn">
                Cancel
              </button>
              <button onClick={handleAddDevice} className="add-btn">
                Add Device
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
