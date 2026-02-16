import React, { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  getScraperJob, getJobSummary, getJobEmployees,
  launchScraperJob, pauseScraperJob,
} from '../services/api'

function JobDetail() {
  const { id } = useParams()
  const [job, setJob] = useState(null)
  const [summary, setSummary] = useState(null)
  const [employees, setEmployees] = useState([])
  const [tab, setTab] = useState('summary')
  const [matchedOnly, setMatchedOnly] = useState(false)
  const [loading, setLoading] = useState(true)

  const loadData = async () => {
    try {
      const [jobRes, summaryRes, empRes] = await Promise.all([
        getScraperJob(id),
        getJobSummary(id).catch(() => ({ data: null })),
        getJobEmployees(id, matchedOnly).catch(() => ({ data: [] })),
      ])
      setJob(jobRes.data)
      setSummary(summaryRes.data)
      setEmployees(empRes.data)
    } catch {
      // Handle error
    }
    setLoading(false)
  }

  useEffect(() => { loadData() }, [id, matchedOnly])

  const handleLaunch = async () => {
    await launchScraperJob(id)
    loadData()
  }

  const handlePause = async () => {
    await pauseScraperJob(id)
    loadData()
  }

  if (loading) return <div className="text-muted">Loading...</div>
  if (!job) return <div className="text-muted">Job not found</div>

  return (
    <div>
      <div className="page-header">
        <div className="flex justify-between items-center">
          <div>
            <h1>{job.name}</h1>
            <p className="text-sm text-muted">Created {new Date(job.created_at).toLocaleString()}</p>
          </div>
          <div className="flex gap-2">
            {job.status !== 'processing' && (
              <button className="btn btn-success" onClick={handleLaunch}>Launch</button>
            )}
            {job.is_enabled && (
              <button className="btn btn-outline" onClick={handlePause}>Pause</button>
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
            <div className="stat-label">LinkedIn Matched</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: 'var(--danger)' }}>{summary.companies_not_found}</div>
            <div className="stat-label">Not Found</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: 'var(--warning)' }}>{summary.close_matches}</div>
            <div className="stat-label">Close Matches</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{summary.employees_scraped}</div>
            <div className="stat-label">Employees Scraped</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: 'var(--accent)' }}>{summary.matching_employees}</div>
            <div className="stat-label">Role Matches</div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-4">
        <button className={`btn ${tab === 'summary' ? 'btn-primary' : 'btn-outline'} btn-sm`} onClick={() => setTab('summary')}>
          Companies
        </button>
        <button className={`btn ${tab === 'employees' ? 'btn-primary' : 'btn-outline'} btn-sm`} onClick={() => setTab('employees')}>
          Employees
        </button>
        <button className={`btn ${tab === 'not_found' ? 'btn-primary' : 'btn-outline'} btn-sm`} onClick={() => setTab('not_found')}>
          Not Found
        </button>
      </div>

      {/* Company results tab */}
      {tab === 'summary' && summary && (
        <div className="card">
          <h2 className="card-title mb-4">Companies with LinkedIn Matches</h2>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Company Name</th>
                  <th>LinkedIn Name</th>
                  <th>LinkedIn URL</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {summary.companies_with_results.map((c, i) => (
                  <tr key={i}>
                    <td>{c.company_name}</td>
                    <td>{c.name_on_linkedin || '-'}</td>
                    <td>
                      {c.linkedin_url ? (
                        <a href={c.linkedin_url} target="_blank" rel="noreferrer" style={{ color: 'var(--accent)' }}>
                          {c.linkedin_url.replace('https://www.linkedin.com/company/', '').replace('/', '')}
                        </a>
                      ) : '-'}
                    </td>
                    <td><ConfidenceBadge confidence={c.match_confidence} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
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
                        <a href={emp.linkedin_url} target="_blank" rel="noreferrer" className="btn btn-outline btn-sm">
                          Profile
                        </a>
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

      {/* Not found tab */}
      {tab === 'not_found' && summary && (
        <div className="card">
          <h2 className="card-title mb-4">Companies Not Found on LinkedIn</h2>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Company Name</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {summary.companies_without_results.map((c, i) => (
                  <tr key={i}>
                    <td>{c.company_name}</td>
                    <td><span className="badge badge-danger">Not Found</span></td>
                  </tr>
                ))}
                {summary.companies_without_results.length === 0 && (
                  <tr><td colSpan={2} className="text-muted text-sm">All companies were found</td></tr>
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

function ConfidenceBadge({ confidence }) {
  const styles = {
    exact: 'badge-success',
    high: 'badge-success',
    medium: 'badge-warning',
    low: 'badge-danger',
    no_match: 'badge-muted',
  }
  return <span className={`badge ${styles[confidence] || 'badge-muted'}`}>{confidence}</span>
}

export default JobDetail
