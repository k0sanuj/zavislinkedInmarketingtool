import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  createDataSource, uploadCsvDataSource,
  getLinkedInAccounts, createScraperJob, launchScraperJob,
  getSheetTabs, getSheetColumns, suggestRoles,
} from '../services/api'

const STEPS = [
  'Data Source',
  'LinkedIn Account',
  'Scraper Settings',
  'Review & Launch',
]

function CreateScraper() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [accounts, setAccounts] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

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

  // Step 2: LinkedIn Account
  const [selectedAccountId, setSelectedAccountId] = useState('')

  // Step 3: Settings
  const [jobName, setJobName] = useState('')
  const [maxEmployees, setMaxEmployees] = useState(30)
  const [maxCompanies, setMaxCompanies] = useState(50)
  const [targetTitles, setTargetTitles] = useState('')
  const [useAiMatching, setUseAiMatching] = useState(true)
  const [aiPrompt, setAiPrompt] = useState('')
  const [frequency, setFrequency] = useState('once')
  const [timesPerDay, setTimesPerDay] = useState(1)
  const [suggestedRoles, setSuggestedRoles] = useState([])

  useEffect(() => {
    getLinkedInAccounts().then(res => setAccounts(res.data)).catch(() => {})
  }, [])

  const loadTabs = async () => {
    if (!sheetUrl) return
    try {
      const res = await getSheetTabs(sheetUrl)
      setTabs(res.data.tabs || [])
    } catch (e) {
      setError('Failed to load sheet tabs. Check the URL and Google credentials.')
    }
  }

  const loadColumns = async () => {
    try {
      const res = await getSheetColumns(sheetUrl, selectedTab || undefined)
      setColumns(res.data.columns || [])
    } catch (e) {
      setError('Failed to load columns.')
    }
  }

  const handleSuggestRoles = async () => {
    if (!targetTitles.trim()) return
    try {
      const titles = targetTitles.split(',').map(t => t.trim()).filter(Boolean)
      const res = await suggestRoles(titles)
      setSuggestedRoles(res.data.suggested_roles || [])
    } catch {
      // Ignore AI errors silently
    }
  }

  const handleCreateDataSource = async () => {
    setLoading(true)
    setError(null)
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
        const values = manualUrls.split('\n').map(u => u.trim()).filter(Boolean)
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

  const handleCreateAndLaunch = async () => {
    setLoading(true)
    setError(null)
    try {
      const titles = targetTitles
        ? targetTitles.split(',').map(t => t.trim()).filter(Boolean)
        : null

      const jobRes = await createScraperJob({
        name: jobName || 'Scraper Job',
        data_source_id: dataSourceId,
        linkedin_account_id: selectedAccountId,
        max_employees_per_company: maxEmployees,
        max_companies_per_launch: maxCompanies,
        target_job_titles: titles,
        use_ai_matching: useAiMatching,
        ai_matching_prompt: aiPrompt || undefined,
        schedule_frequency: frequency,
        schedule_times_per_day: timesPerDay,
      })

      // Launch immediately
      await launchScraperJob(jobRes.data.id)
      navigate(`/scrapers/${jobRes.data.id}`)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to create job')
    }
    setLoading(false)
  }

  return (
    <div>
      <div className="page-header">
        <h1>Create Scraper</h1>
        <p>Set up a new LinkedIn company scraper in 4 steps</p>
      </div>

      {/* Steps indicator */}
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
          <h2 className="card-title mb-4">Connect Your Data Source</h2>

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
                <label>Google Sheet URL</label>
                <div className="flex gap-2">
                  <input className="form-input" value={sheetUrl} onChange={e => setSheetUrl(e.target.value)} placeholder="https://docs.google.com/spreadsheets/d/..." />
                  <button className="btn btn-outline btn-sm" onClick={loadTabs}>Load</button>
                </div>
              </div>

              {tabs.length > 0 && (
                <div className="form-group">
                  <label>Sheet Tab</label>
                  <select className="form-select" value={selectedTab} onChange={e => { setSelectedTab(e.target.value); loadColumns(); }}>
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
          <h2 className="card-title mb-4">Connect LinkedIn Account</h2>
          <p className="text-sm text-muted mb-4">
            Select a connected LinkedIn Sales Navigator account to use for scraping.
          </p>

          {accounts.length === 0 ? (
            <div>
              <p className="text-muted">No LinkedIn accounts connected yet.</p>
              <button className="btn btn-outline mt-4" onClick={() => navigate('/accounts')}>
                Connect Account
              </button>
            </div>
          ) : (
            <>
              <div className="form-group">
                <label>LinkedIn Account</label>
                <select className="form-select" value={selectedAccountId} onChange={e => setSelectedAccountId(e.target.value)}>
                  <option value="">Select account...</option>
                  {accounts.map(a => (
                    <option key={a.id} value={a.id}>
                      {a.name} {a.is_sales_navigator ? '(Sales Navigator)' : ''}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex gap-2 mt-4">
                <button className="btn btn-outline" onClick={() => setStep(0)}>Back</button>
                <button className="btn btn-primary" onClick={() => setStep(2)} disabled={!selectedAccountId}>
                  Continue
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* Step 3: Settings */}
      {step === 2 && (
        <div className="card">
          <h2 className="card-title mb-4">Scraper Settings</h2>

          <div className="form-group">
            <label>Job Name</label>
            <input className="form-input" value={jobName} onChange={e => setJobName(e.target.value)} placeholder="e.g. Dubai Dental Clinics Scrape" />
          </div>

          <div className="flex gap-4">
            <div className="form-group" style={{ flex: 1 }}>
              <label>Max Employees per Company</label>
              <input className="form-input" type="number" value={maxEmployees} onChange={e => setMaxEmployees(Number(e.target.value))} />
            </div>
            <div className="form-group" style={{ flex: 1 }}>
              <label>Max Companies per Launch</label>
              <input className="form-input" type="number" value={maxCompanies} onChange={e => setMaxCompanies(Number(e.target.value))} />
            </div>
          </div>

          <div className="form-group">
            <label>Target Job Titles (comma-separated)</label>
            <div className="flex gap-2">
              <input className="form-input" value={targetTitles} onChange={e => setTargetTitles(e.target.value)} placeholder="e.g. Clinic Administrator, Practice Manager, Operations Director" />
              <button className="btn btn-outline btn-sm" onClick={handleSuggestRoles}>AI Suggest</button>
            </div>
            {suggestedRoles.length > 0 && (
              <div className="mt-4">
                <p className="text-sm text-muted mb-4">AI-suggested related roles (click to add):</p>
                <div className="flex gap-2" style={{ flexWrap: 'wrap' }}>
                  {suggestedRoles.map(role => (
                    <button
                      key={role}
                      className="btn btn-outline btn-sm"
                      onClick={() => {
                        const current = targetTitles ? targetTitles + ', ' : ''
                        setTargetTitles(current + role)
                      }}
                    >
                      + {role}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="form-group">
            <label className="flex items-center gap-2">
              <label className="toggle">
                <input type="checkbox" checked={useAiMatching} onChange={e => setUseAiMatching(e.target.checked)} />
                <span className="toggle-slider"></span>
              </label>
              Use AI Role Matching
            </label>
          </div>

          {useAiMatching && (
            <div className="form-group">
              <label>Custom AI Matching Prompt (optional)</label>
              <textarea className="form-textarea" value={aiPrompt} onChange={e => setAiPrompt(e.target.value)} placeholder="e.g. Find decision-makers in clinic operations, purchasing, and administration" />
            </div>
          )}

          <h3 className="card-title mt-4 mb-4">Schedule</h3>
          <div className="flex gap-4">
            <div className="form-group" style={{ flex: 1 }}>
              <label>Frequency</label>
              <select className="form-select" value={frequency} onChange={e => setFrequency(e.target.value)}>
                <option value="once">Run Once</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </div>
            {frequency !== 'once' && (
              <div className="form-group" style={{ flex: 1 }}>
                <label>Times per Day</label>
                <input className="form-input" type="number" min={1} max={24} value={timesPerDay} onChange={e => setTimesPerDay(Number(e.target.value))} />
              </div>
            )}
          </div>

          <div className="flex gap-2 mt-4">
            <button className="btn btn-outline" onClick={() => setStep(1)}>Back</button>
            <button className="btn btn-primary" onClick={() => setStep(3)}>Review</button>
          </div>
        </div>
      )}

      {/* Step 4: Review & Launch */}
      {step === 3 && (
        <div className="card">
          <h2 className="card-title mb-4">Review & Launch</h2>

          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-label">Job Name</div>
              <div style={{ fontSize: 16, fontWeight: 600, marginTop: 4 }}>{jobName || 'Unnamed Job'}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Max Employees/Company</div>
              <div className="stat-value">{maxEmployees}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Max Companies</div>
              <div className="stat-value">{maxCompanies}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Schedule</div>
              <div style={{ fontSize: 16, fontWeight: 600, marginTop: 4 }}>{frequency}</div>
            </div>
          </div>

          {targetTitles && (
            <div className="mb-4">
              <span className="text-sm text-muted">Target Titles: </span>
              <span className="text-sm">{targetTitles}</span>
            </div>
          )}

          <div className="mb-4">
            <span className="text-sm text-muted">AI Matching: </span>
            <span className={`badge ${useAiMatching ? 'badge-success' : 'badge-muted'}`}>
              {useAiMatching ? 'Enabled' : 'Disabled'}
            </span>
          </div>

          <div className="flex gap-2 mt-4">
            <button className="btn btn-outline" onClick={() => setStep(2)}>Back</button>
            <button className="btn btn-success" onClick={handleCreateAndLaunch} disabled={loading}>
              {loading ? 'Launching...' : 'Launch Scraper'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default CreateScraper
