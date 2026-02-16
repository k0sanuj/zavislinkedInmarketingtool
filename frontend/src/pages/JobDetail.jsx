import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  getScraperJob, getJobSummary, getJobCompanies, getJobEmployees,
  launchScraperJob, pauseScraperJob,
  createEmployeeScraping, getLinkedInAccounts,
  suggestRolesFromGoal,
} from '../services/api'

function JobDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [job, setJob] = useState(null)
  const [summary, setSummary] = useState(null)
  const [companies, setCompanies] = useState([])
  const [employees, setEmployees] = useState([])
  const [tab, setTab] = useState('all')
  const [matchedOnly, setMatchedOnly] = useState(false)
  const [loading, setLoading] = useState(true)

  // Employee scraping panel
  const [showScrapePanel, setShowScrapePanel] = useState(false)
  const [selectedCompanies, setSelectedCompanies] = useState(new Set())
  const [accounts, setAccounts] = useState([])
  const [selectedAccountId, setSelectedAccountId] = useState('')
  const [goalDescription, setGoalDescription] = useState('')
  const [suggestedRoles, setSuggestedRoles] = useState([])
  const [selectedRoles, setSelectedRoles] = useState([])
  const [customRole, setCustomRole] = useState('')
  const [maxEmployees, setMaxEmployees] = useState(30)
  const [useAiMatching, setUseAiMatching] = useState(true)
  const [aiPrompt, setAiPrompt] = useState('')
  const [scrapeLoading, setScrapeLoading] = useState(false)
  const [scrapeError, setScrapeError] = useState(null)
  const [roleLoading, setRoleLoading] = useState(false)

  const isDiscovery = !job?.job_type || job?.job_type === 'company_discovery'
  const isEmployeeScraping = job?.job_type === 'employee_scraping'

  const loadData = async () => {
    try {
      const [jobRes, summaryRes] = await Promise.all([
        getScraperJob(id),
        getJobSummary(id).catch(() => ({ data: null })),
      ])
      setJob(jobRes.data)
      setSummary(summaryRes.data)

      // Load companies for discovery jobs, employees for scraping jobs
      if (!jobRes.data.job_type || jobRes.data.job_type === 'company_discovery') {
        const compRes = await getJobCompanies(id, tab === 'employees' ? 'all' : tab).catch(() => ({ data: [] }))
        setCompanies(compRes.data)
      }
      if (jobRes.data.job_type === 'employee_scraping' || tab === 'employees') {
        const empRes = await getJobEmployees(id, matchedOnly).catch(() => ({ data: [] }))
        setEmployees(empRes.data)
      }
    } catch {
      // Handle error
    }
    setLoading(false)
  }

  useEffect(() => { loadData() }, [id, tab, matchedOnly])

  useEffect(() => {
    if (showScrapePanel && accounts.length === 0) {
      getLinkedInAccounts().then(res => setAccounts(res.data)).catch(() => {})
    }
  }, [showScrapePanel])

  const handleLaunch = async () => { await launchScraperJob(id); loadData() }
  const handlePause = async () => { await pauseScraperJob(id); loadData() }

  const toggleCompany = (companyId) => {
    setSelectedCompanies(prev => {
      const next = new Set(prev)
      if (next.has(companyId)) next.delete(companyId)
      else next.add(companyId)
      return next
    })
  }

  const selectAllWithLinkedin = () => {
    const withLinkedin = companies.filter(c => c.linkedin_url)
    setSelectedCompanies(new Set(withLinkedin.map(c => c.id)))
  }

  const handleSuggestRoles = async () => {
    if (!goalDescription.trim()) return
    setRoleLoading(true)
    try {
      const res = await suggestRolesFromGoal(goalDescription)
      setSuggestedRoles(res.data.suggested_roles || [])
    } catch {
      // Silently fail
    }
    setRoleLoading(false)
  }

  const addRole = (role) => {
    if (!selectedRoles.includes(role)) setSelectedRoles([...selectedRoles, role])
  }
  const removeRole = (role) => setSelectedRoles(selectedRoles.filter(r => r !== role))
  const addCustomRole = () => {
    if (customRole.trim() && !selectedRoles.includes(customRole.trim())) {
      setSelectedRoles([...selectedRoles, customRole.trim()])
      setCustomRole('')
    }
  }

  const handleLaunchEmployeeScraping = async () => {
    if (selectedCompanies.size === 0 || selectedRoles.length === 0 || !selectedAccountId) return
    setScrapeLoading(true); setScrapeError(null)
    try {
      const jobRes = await createEmployeeScraping({
        name: `Employee Scrape - ${job.name}`,
        parent_job_id: id,
        linkedin_account_id: selectedAccountId,
        selected_company_ids: Array.from(selectedCompanies),
        target_job_titles: selectedRoles,
        max_employees_per_company: maxEmployees,
        use_ai_matching: useAiMatching,
        ai_matching_prompt: aiPrompt || undefined,
      })
      await launchScraperJob(jobRes.data.id)
      navigate(`/scrapers/${jobRes.data.id}`)
    } catch (e) {
      setScrapeError(e.response?.data?.detail || 'Failed to launch employee scraping')
    }
    setScrapeLoading(false)
  }

  if (loading) return <div className="text-muted">Loading...</div>
  if (!job) return <div className="text-muted">Job not found</div>

  const withLinkedinCount = companies.filter(c => c.linkedin_url).length
  const withoutLinkedinCount = companies.filter(c => !c.linkedin_url).length

  return (
    <div>
      <div className="page-header">
        <div className="flex justify-between items-center">
          <div>
            <h1>{job.name}</h1>
            <p className="text-sm text-muted">
              {isDiscovery ? 'Company Discovery' : 'Employee Scraping'}
              {' \u2022 '}Created {new Date(job.created_at).toLocaleString()}
            </p>
          </div>
          <div className="flex gap-2">
            <StatusBadge status={job.status} />
            {job.status !== 'processing' && (
              <button className="btn btn-success btn-sm" onClick={handleLaunch}>Re-run</button>
            )}
            {job.is_enabled && (
              <button className="btn btn-outline btn-sm" onClick={handlePause}>Pause</button>
            )}
          </div>
        </div>
      </div>

      {/* Stats */}
      {summary && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value">{summary.total_companies}</div>
            <div className="stat-label">Total Companies</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: 'var(--success)' }}>{summary.companies_matched}</div>
            <div className="stat-label">With LinkedIn</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: 'var(--danger)' }}>{summary.companies_not_found}</div>
            <div className="stat-label">Not Found</div>
          </div>
          {isEmployeeScraping && (
            <>
              <div className="stat-card">
                <div className="stat-value">{summary.employees_scraped}</div>
                <div className="stat-label">Employees</div>
              </div>
              <div className="stat-card">
                <div className="stat-value" style={{ color: 'var(--accent)' }}>{summary.matching_employees}</div>
                <div className="stat-label">Role Matches</div>
              </div>
            </>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-4">
        {isDiscovery && (
          <>
            <button className={`btn ${tab === 'all' ? 'btn-primary' : 'btn-outline'} btn-sm`} onClick={() => setTab('all')}>
              All ({companies.length || summary?.total_companies || 0})
            </button>
            <button className={`btn ${tab === 'with_linkedin' ? 'btn-primary' : 'btn-outline'} btn-sm`} onClick={() => setTab('with_linkedin')}>
              With LinkedIn ({withLinkedinCount || summary?.companies_matched || 0})
            </button>
            <button className={`btn ${tab === 'without_linkedin' ? 'btn-primary' : 'btn-outline'} btn-sm`} onClick={() => setTab('without_linkedin')}>
              Without LinkedIn ({withoutLinkedinCount || summary?.companies_not_found || 0})
            </button>
          </>
        )}
        {(isEmployeeScraping || (isDiscovery && summary?.employees_scraped > 0)) && (
          <button className={`btn ${tab === 'employees' ? 'btn-primary' : 'btn-outline'} btn-sm`} onClick={() => setTab('employees')}>
            Employees ({summary?.employees_scraped || 0})
          </button>
        )}
      </div>

      {/* Company table (for discovery jobs) */}
      {isDiscovery && tab !== 'employees' && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              {tab === 'all' ? 'All Companies' : tab === 'with_linkedin' ? 'Companies with LinkedIn' : 'Companies without LinkedIn'}
            </h2>
            {tab !== 'without_linkedin' && job.status === 'completed' && (
              <div className="flex gap-2">
                {selectedCompanies.size > 0 && (
                  <button className="btn btn-primary btn-sm" onClick={() => setShowScrapePanel(true)}>
                    Scrape Employees ({selectedCompanies.size} selected)
                  </button>
                )}
                <button className="btn btn-outline btn-sm" onClick={selectAllWithLinkedin}>
                  Select All with LinkedIn
                </button>
              </div>
            )}
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  {tab !== 'without_linkedin' && <th style={{ width: 40 }}></th>}
                  <th>Company Name</th>
                  <th>LinkedIn Name</th>
                  <th>LinkedIn URL</th>
                  <th>Employees</th>
                  <th>Industry</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {companies.map(c => (
                  <tr key={c.id}>
                    {tab !== 'without_linkedin' && (
                      <td>
                        {c.linkedin_url && (
                          <input
                            type="checkbox"
                            checked={selectedCompanies.has(c.id)}
                            onChange={() => toggleCompany(c.id)}
                          />
                        )}
                      </td>
                    )}
                    <td>{c.name}</td>
                    <td>{c.name_on_linkedin || <span className="text-muted">NA</span>}</td>
                    <td>
                      {c.linkedin_url ? (
                        <a href={c.linkedin_url} target="_blank" rel="noreferrer" style={{ color: 'var(--accent)' }}>
                          {c.linkedin_url.replace('https://www.linkedin.com/company/', '').replace('/', '')}
                        </a>
                      ) : <span className="text-muted">NA</span>}
                    </td>
                    <td>{c.employee_count != null ? c.employee_count.toLocaleString() : <span className="text-muted">NA</span>}</td>
                    <td>{c.industry || <span className="text-muted">NA</span>}</td>
                    <td><ConfidenceBadge confidence={c.match_confidence} /></td>
                  </tr>
                ))}
                {companies.length === 0 && (
                  <tr><td colSpan={7} className="text-muted text-sm">
                    {job.status === 'processing' ? 'Discovery in progress...' : 'No companies found'}
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Employee Scraping Panel */}
      {showScrapePanel && (
        <div className="card" style={{ borderColor: 'var(--accent)', marginBottom: 16 }}>
          <h2 className="card-title mb-4">Scrape Employees from Selected Companies</h2>
          <p className="text-sm text-muted mb-4">{selectedCompanies.size} companies selected</p>

          {scrapeError && (
            <div style={{ color: 'var(--danger)', marginBottom: 12 }}>{scrapeError}</div>
          )}

          <div className="form-group">
            <label>LinkedIn Account (Sales Navigator recommended)</label>
            <select className="form-select" value={selectedAccountId} onChange={e => setSelectedAccountId(e.target.value)}>
              <option value="">Select account...</option>
              {accounts.map(a => (
                <option key={a.id} value={a.id}>{a.name} {a.is_sales_navigator ? '(Sales Nav)' : ''}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Describe your goal</label>
            <div className="flex gap-2">
              <textarea
                className="form-textarea"
                value={goalDescription}
                onChange={e => setGoalDescription(e.target.value)}
                placeholder="e.g. I want to reach decision-makers at dental clinics who handle purchasing and operations"
                rows={2}
              />
              <button className="btn btn-primary btn-sm" onClick={handleSuggestRoles} disabled={roleLoading} style={{ alignSelf: 'flex-end' }}>
                {roleLoading ? 'Thinking...' : 'AI Suggest Roles'}
              </button>
            </div>
          </div>

          {suggestedRoles.length > 0 && (
            <div className="form-group">
              <label className="text-sm text-muted">AI-Suggested Roles (click to add):</label>
              <div className="flex gap-2" style={{ flexWrap: 'wrap', marginTop: 8 }}>
                {suggestedRoles.map(role => (
                  <button
                    key={role}
                    className={`btn btn-sm ${selectedRoles.includes(role) ? 'btn-primary' : 'btn-outline'}`}
                    onClick={() => selectedRoles.includes(role) ? removeRole(role) : addRole(role)}
                  >
                    {selectedRoles.includes(role) ? '\u2713 ' : '+ '}{role}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="form-group">
            <label>Selected Roles ({selectedRoles.length})</label>
            {selectedRoles.length > 0 ? (
              <div className="flex gap-2" style={{ flexWrap: 'wrap', marginBottom: 8 }}>
                {selectedRoles.map(role => (
                  <span key={role} className="badge badge-info" style={{ cursor: 'pointer' }} onClick={() => removeRole(role)}>
                    {role} &times;
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted">No roles selected yet. Use AI suggest or add manually below.</p>
            )}
            <div className="flex gap-2">
              <input className="form-input" value={customRole} onChange={e => setCustomRole(e.target.value)} placeholder="Add custom role..." onKeyDown={e => e.key === 'Enter' && addCustomRole()} />
              <button className="btn btn-outline btn-sm" onClick={addCustomRole}>Add</button>
            </div>
          </div>

          <div className="flex gap-4">
            <div className="form-group" style={{ flex: 1 }}>
              <label>Max Employees per Company</label>
              <input className="form-input" type="number" value={maxEmployees} onChange={e => setMaxEmployees(Number(e.target.value))} />
            </div>
            <div className="form-group" style={{ flex: 1 }}>
              <label className="flex items-center gap-2">
                <label className="toggle">
                  <input type="checkbox" checked={useAiMatching} onChange={e => setUseAiMatching(e.target.checked)} />
                  <span className="toggle-slider"></span>
                </label>
                AI Role Matching
              </label>
            </div>
          </div>

          {useAiMatching && (
            <div className="form-group">
              <label>Custom AI Matching Prompt (optional)</label>
              <textarea className="form-textarea" value={aiPrompt} onChange={e => setAiPrompt(e.target.value)} placeholder="e.g. Focus on people who make purchasing decisions" rows={2} />
            </div>
          )}

          <div className="flex gap-2 mt-4">
            <button className="btn btn-outline" onClick={() => setShowScrapePanel(false)}>Cancel</button>
            <button
              className="btn btn-success"
              onClick={handleLaunchEmployeeScraping}
              disabled={scrapeLoading || selectedRoles.length === 0 || !selectedAccountId}
            >
              {scrapeLoading ? 'Launching...' : `Scrape Employees (${selectedCompanies.size} companies)`}
            </button>
          </div>
        </div>
      )}

      {/* Employees tab */}
      {tab === 'employees' && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Scraped Employees</h2>
            <label className="flex items-center gap-2 text-sm">
              <label className="toggle">
                <input type="checkbox" checked={matchedOnly} onChange={e => setMatchedOnly(e.target.checked)} />
                <span className="toggle-slider"></span>
              </label>
              Show matched only
            </label>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Job Title</th>
                  <th>Company</th>
                  <th>Location</th>
                  <th>Match</th>
                  <th>LinkedIn</th>
                </tr>
              </thead>
              <tbody>
                {employees.map(emp => (
                  <tr key={emp.id}>
                    <td>{emp.full_name}</td>
                    <td>{emp.job_title || '-'}</td>
                    <td>{emp.company_name || '-'}</td>
                    <td>{emp.location || '-'}</td>
                    <td>
                      {emp.is_match !== null ? (
                        <span className={`badge ${emp.is_match ? 'badge-success' : 'badge-muted'}`}>
                          {emp.is_match ? emp.match_confidence : 'No match'}
                        </span>
                      ) : '-'}
                    </td>
                    <td>
                      {emp.linkedin_url ? (
                        <a href={emp.linkedin_url} target="_blank" rel="noreferrer" className="btn btn-outline btn-sm">Profile</a>
                      ) : '-'}
                    </td>
                  </tr>
                ))}
                {employees.length === 0 && (
                  <tr><td colSpan={6} className="text-muted text-sm">No employees scraped yet</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Error info */}
      {job.last_error && (
        <div className="card" style={{ borderColor: 'var(--danger)' }}>
          <h3 style={{ color: 'var(--danger)' }}>Last Error</h3>
          <p className="text-sm mt-4">{job.last_error}</p>
        </div>
      )}
    </div>
  )
}

function StatusBadge({ status }) {
  const styles = {
    pending: 'badge-muted', active: 'badge-info', processing: 'badge-warning',
    completed: 'badge-success', failed: 'badge-danger', paused: 'badge-muted',
  }
  return <span className={`badge ${styles[status] || 'badge-muted'}`}>{status}</span>
}

function ConfidenceBadge({ confidence }) {
  if (!confidence) return <span className="badge badge-danger">NA</span>
  const styles = {
    exact: 'badge-success', high: 'badge-success', medium: 'badge-warning',
    low: 'badge-danger', no_match: 'badge-muted',
  }
  return <span className={`badge ${styles[confidence] || 'badge-muted'}`}>{confidence}</span>
}

export default JobDetail
