import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  createDataSource, uploadCsvDataSource,
  getLinkedInAccounts, createCompanyDiscovery, launchScraperJob,
  getSheetTabs, getSheetColumns,
  getGoogleAuthUrl, getGoogleStatus, disconnectGoogle,
} from '../services/api'

const STEPS = [
  'Data Source',
  'LinkedIn Account',
  'Review & Launch',
]

function CreateScraper() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [accounts, setAccounts] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  // Google OAuth state
  const [googleConnected, setGoogleConnected] = useState(false)
  const [googleEmail, setGoogleEmail] = useState(null)
  const [googleLoading, setGoogleLoading] = useState(true)

  // Step 1: Data Source
  const [sourceType, setSourceType] = useState('google_sheet')
  const [sheetUrl, setSheetUrl] = useState('')
  const [tabs, setTabs] = useState([])
  const [selectedTab, setSelectedTab] = useState('')
  const [columns, setColumns] = useState([])
  const [selectedColumn, setSelectedColumn] = useState('')
  const [columnType, setColumnType] = useState('company_name')
  const [csvFile, setCsvFile] = useState(null)
  const [manualUrls, setManualUrls] = useState('')
  const [dataSourceId, setDataSourceId] = useState(null)
  const [sourceName, setSourceName] = useState('')
  const [maxCompanies, setMaxCompanies] = useState(50)

  // Step 2: LinkedIn Account
  const [selectedAccountId, setSelectedAccountId] = useState('')

  // Job name
  const [jobName, setJobName] = useState('')

  const checkGoogleStatus = useCallback(async () => {
    try {
      const res = await getGoogleStatus()
      setGoogleConnected(res.data.connected)
      setGoogleEmail(res.data.email || null)
    } catch {
      setGoogleConnected(false)
    }
    setGoogleLoading(false)
  }, [])

  useEffect(() => {
    getLinkedInAccounts().then(res => setAccounts(res.data)).catch(() => {})
    checkGoogleStatus()
  }, [checkGoogleStatus])

  useEffect(() => {
    const handler = (event) => {
      if (event.data?.type === 'google-oauth-success') checkGoogleStatus()
    }
    window.addEventListener('message', handler)
    return () => window.removeEventListener('message', handler)
  }, [checkGoogleStatus])

  const handleConnectGoogle = async () => {
    setError(null)
    try {
      const res = await getGoogleAuthUrl()
      const w = 500, h = 600
      const left = window.screenX + (window.outerWidth - w) / 2
      const top = window.screenY + (window.outerHeight - h) / 2
      const popup = window.open(
        res.data.auth_url, 'google-oauth',
        `width=${w},height=${h},left=${left},top=${top},toolbar=no,menubar=no`
      )
      if (popup) {
        const timer = setInterval(() => {
          if (popup.closed) { clearInterval(timer); checkGoogleStatus() }
        }, 500)
      }
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to start Google authorization.')
    }
  }

  const handleDisconnectGoogle = async () => {
    try {
      await disconnectGoogle()
      setGoogleConnected(false); setGoogleEmail(null); setTabs([]); setColumns([])
    } catch { setError('Failed to disconnect Google account.') }
  }

  const loadTabs = async () => {
    if (!sheetUrl) return
    setError(null)
    try {
      const res = await getSheetTabs(sheetUrl)
      setTabs(res.data.tabs || [])
    } catch (e) {
      setError(e.response?.status === 401
        ? 'Google account not connected.'
        : (e.response?.data?.detail || 'Failed to load sheet tabs.'))
    }
  }

  const loadColumns = async () => {
    setError(null)
    try {
      const res = await getSheetColumns(sheetUrl, selectedTab || undefined)
      setColumns(res.data.columns || [])
    } catch (e) {
      setError(e.response?.status === 401
        ? 'Google account not connected.'
        : (e.response?.data?.detail || 'Failed to load columns.'))
    }
  }

  const handleCreateDataSource = async () => {
    setLoading(true); setError(null)
    try {
      let res
      if (sourceType === 'google_sheet') {
        res = await createDataSource({
          name: sourceName || 'Google Sheet Import',
          source_type: 'google_sheet',
          google_sheet_url: sheetUrl,
          sheet_tab_name: selectedTab || undefined,
          column_name: selectedColumn,
          column_type: columnType,
        })
      } else if (sourceType === 'csv_upload') {
        const formData = new FormData()
        formData.append('name', sourceName || 'CSV Upload')
        formData.append('column_name', selectedColumn)
        formData.append('column_type', columnType)
        formData.append('file', csvFile)
        res = await uploadCsvDataSource(formData)
      } else {
        res = await createDataSource({
          name: sourceName || 'Manual URLs',
          source_type: 'manual',
          column_type: 'linkedin_url',
        })
      }
      setDataSourceId(res.data.id)
      setStep(1)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to create data source')
    }
    setLoading(false)
  }

  const handleLaunchDiscovery = async () => {
    setLoading(true); setError(null)
    try {
      const jobRes = await createCompanyDiscovery({
        name: jobName || `Company Discovery - ${sourceName || 'Untitled'}`,
        data_source_id: dataSourceId,
        linkedin_account_id: selectedAccountId,
        max_companies_per_launch: maxCompanies,
      })
      await launchScraperJob(jobRes.data.id)
      navigate(`/scrapers/${jobRes.data.id}`)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to launch discovery job')
    }
    setLoading(false)
  }

  return (
    <div>
      <div className="page-header">
        <h1>Discover Company LinkedIn Pages</h1>
        <p>Upload your company list and we'll find their LinkedIn pages, employee counts, and more</p>
      </div>

      <div className="steps">
        {STEPS.map((s, i) => (
          <div key={i} className={`step ${i === step ? 'active' : ''} ${i < step ? 'completed' : ''}`}>
            <span className="step-number">{i < step ? '\u2713' : i + 1}</span>
            {s}
          </div>
        ))}
      </div>

      {error && (
        <div className="card" style={{ borderColor: 'var(--danger)', marginBottom: 16 }}>
          <span style={{ color: 'var(--danger)' }}>{error}</span>
        </div>
      )}

      {/* Step 1: Data Source */}
      {step === 0 && (
        <div className="card">
          <h2 className="card-title mb-4">Upload Your Company List</h2>

          <div className="form-group">
            <label>Source Name</label>
            <input className="form-input" value={sourceName} onChange={e => setSourceName(e.target.value)} placeholder="e.g. Dubai Clinics List" />
          </div>

          <div className="form-group">
            <label>Source Type</label>
            <select className="form-select" value={sourceType} onChange={e => setSourceType(e.target.value)}>
              <option value="google_sheet">Google Sheet</option>
              <option value="csv_upload">Upload CSV</option>
              <option value="manual">Manual URL List</option>
            </select>
          </div>

          {sourceType === 'google_sheet' && (
            <>
              <div className="form-group">
                <label>Google Account</label>
                {googleLoading ? (
                  <p className="text-sm text-muted">Checking Google connection...</p>
                ) : googleConnected ? (
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    padding: '10px 14px', borderRadius: 8,
                    background: 'var(--success-bg, #e6f9e6)', border: '1px solid var(--success, #22c55e)',
                  }}>
                    <span style={{ color: 'var(--success, #22c55e)', fontWeight: 600, fontSize: 18 }}>&#10003;</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 500 }}>Connected{googleEmail ? ` as ${googleEmail}` : ''}</div>
                      <div className="text-sm text-muted">Google Sheets access authorized</div>
                    </div>
                    <button className="btn btn-outline btn-sm" style={{ color: 'var(--danger)', borderColor: 'var(--danger)' }} onClick={handleDisconnectGoogle}>Disconnect</button>
                  </div>
                ) : (
                  <div>
                    <button className="btn btn-primary" onClick={handleConnectGoogle}>Connect Google Account</button>
                    <p className="text-sm text-muted" style={{ marginTop: 8 }}>Sign in with Google to allow access to your Google Sheets.</p>
                  </div>
                )}
              </div>

              {googleConnected && (
                <>
                  <div className="form-group">
                    <label>Google Sheet URL</label>
                    <div className="flex gap-2">
                      <input className="form-input" value={sheetUrl} onChange={e => setSheetUrl(e.target.value)} placeholder="https://docs.google.com/spreadsheets/d/..." />
                      <button className="btn btn-outline btn-sm" onClick={loadTabs}>Load</button>
                    </div>
                  </div>
                  {tabs.length > 0 && (
                    <div className="form-group">
                      <label>Sheet Tab</label>
                      <select className="form-select" value={selectedTab} onChange={e => { setSelectedTab(e.target.value); loadColumns() }}>
                        <option value="">First tab</option>
                        {tabs.map(t => <option key={t} value={t}>{t}</option>)}
                      </select>
                    </div>
                  )}
                  {(tabs.length > 0 || sheetUrl) && (
                    <button className="btn btn-outline btn-sm mb-4" onClick={loadColumns}>Load Columns</button>
                  )}
                  {columns.length > 0 && (
                    <div className="form-group">
                      <label>Select Column</label>
                      <select className="form-select" value={selectedColumn} onChange={e => setSelectedColumn(e.target.value)}>
                        <option value="">Select column...</option>
                        {columns.map(c => <option key={c} value={c}>{c}</option>)}
                      </select>
                    </div>
                  )}
                </>
              )}
            </>
          )}

          {sourceType === 'csv_upload' && (
            <>
              <div className="form-group">
                <label>Upload CSV File</label>
                <input type="file" accept=".csv" onChange={e => setCsvFile(e.target.files[0])} />
              </div>
              <div className="form-group">
                <label>Column Name</label>
                <input className="form-input" value={selectedColumn} onChange={e => setSelectedColumn(e.target.value)} placeholder="e.g. Company Name" />
              </div>
            </>
          )}

          {sourceType === 'manual' && (
            <div className="form-group">
              <label>LinkedIn Company URLs (one per line)</label>
              <textarea className="form-textarea" rows={8} value={manualUrls} onChange={e => setManualUrls(e.target.value)} placeholder="https://www.linkedin.com/company/..." />
            </div>
          )}

          <div className="form-group">
            <label>Column Contains</label>
            <select className="form-select" value={columnType} onChange={e => setColumnType(e.target.value)}>
              <option value="company_name">Company Names (will search for LinkedIn URLs)</option>
              <option value="linkedin_url">LinkedIn Company URLs (already have URLs)</option>
            </select>
          </div>

          <button className="btn btn-primary mt-4" onClick={handleCreateDataSource} disabled={loading}>
            {loading ? 'Processing...' : 'Save & Continue'}
          </button>
        </div>
      )}

      {/* Step 2: LinkedIn Account */}
      {step === 1 && (
        <div className="card">
          <h2 className="card-title mb-4">Select LinkedIn Account</h2>
          <p className="text-sm text-muted mb-4">Choose which LinkedIn account to use for discovering company pages.</p>

          {accounts.length === 0 ? (
            <div>
              <p className="text-muted">No LinkedIn accounts connected yet.</p>
              <button className="btn btn-outline mt-4" onClick={() => navigate('/accounts')}>Connect Account</button>
            </div>
          ) : (
            <>
              <div className="form-group">
                <label>LinkedIn Account</label>
                <select className="form-select" value={selectedAccountId} onChange={e => setSelectedAccountId(e.target.value)}>
                  <option value="">Select account...</option>
                  {accounts.map(a => (
                    <option key={a.id} value={a.id}>{a.name} {a.is_sales_navigator ? '(Sales Nav)' : ''}</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-2 mt-4">
                <button className="btn btn-outline" onClick={() => setStep(0)}>Back</button>
                <button className="btn btn-primary" onClick={() => setStep(2)} disabled={!selectedAccountId}>Continue</button>
              </div>
            </>
          )}
        </div>
      )}

      {/* Step 3: Review & Launch */}
      {step === 2 && (
        <div className="card">
          <h2 className="card-title mb-4">Review & Launch Discovery</h2>

          <div className="form-group">
            <label>Job Name</label>
            <input className="form-input" value={jobName} onChange={e => setJobName(e.target.value)} placeholder={`Company Discovery - ${sourceName || 'Untitled'}`} />
          </div>

          <div className="form-group">
            <label>Max Companies to Process</label>
            <input className="form-input" type="number" value={maxCompanies} onChange={e => setMaxCompanies(Number(e.target.value))} />
          </div>

          <div className="card" style={{ background: 'var(--bg-primary)', marginTop: 16 }}>
            <h3 className="text-sm" style={{ fontWeight: 600, marginBottom: 8 }}>What happens next:</h3>
            <ol className="text-sm text-muted" style={{ paddingLeft: 20, lineHeight: 1.8 }}>
              <li>We search LinkedIn for each company in your list</li>
              <li>For each match, we scrape the company's LinkedIn page (name, industry, employee count, etc.)</li>
              <li>Results appear in a table with "With LinkedIn" and "Without LinkedIn" tabs</li>
              <li>From there, you can select companies and scrape their employees</li>
            </ol>
          </div>

          <div className="flex gap-2 mt-4">
            <button className="btn btn-outline" onClick={() => setStep(1)}>Back</button>
            <button className="btn btn-success" onClick={handleLaunchDiscovery} disabled={loading}>
              {loading ? 'Launching...' : 'Launch Company Discovery'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default CreateScraper
