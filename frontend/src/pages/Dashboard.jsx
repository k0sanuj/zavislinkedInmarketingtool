import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getScraperJobs, getLinkedInAccounts } from '../services/api'

function Dashboard() {
  const [jobs, setJobs] = useState([])
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getScraperJobs().catch(() => ({ data: [] })),
      getLinkedInAccounts().catch(() => ({ data: [] })),
    ]).then(([jobsRes, accountsRes]) => {
      setJobs(jobsRes.data)
      setAccounts(accountsRes.data)
      setLoading(false)
    })
  }, [])

  const activeJobs = jobs.filter(j => j.is_enabled)
  const totalEmployees = jobs.reduce((sum, j) => sum + (j.employees_scraped || 0), 0)
  const totalCompanies = jobs.reduce((sum, j) => sum + (j.companies_processed || 0), 0)

  if (loading) return <div className="text-muted">Loading...</div>

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Overview of your LinkedIn scraping operations</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{jobs.length}</div>
          <div className="stat-label">Total Scrapers</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{activeJobs.length}</div>
          <div className="stat-label">Active Jobs</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{totalCompanies}</div>
          <div className="stat-label">Companies Processed</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{totalEmployees}</div>
          <div className="stat-label">Employees Scraped</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{accounts.length}</div>
          <div className="stat-label">LinkedIn Accounts</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Recent Scraper Jobs</h2>
          <Link to="/create" className="btn btn-primary btn-sm">Create New</Link>
        </div>

        {jobs.length === 0 ? (
          <div className="text-muted text-sm">
            No scraper jobs yet. <Link to="/create">Create your first scraper</Link> to get started.
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Status</th>
                  <th>Companies</th>
                  <th>Employees</th>
                  <th>Active</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {jobs.slice(0, 10).map(job => (
                  <tr key={job.id}>
                    <td><Link to={`/scrapers/${job.id}`}>{job.name}</Link></td>
                    <td><StatusBadge status={job.status} /></td>
                    <td>{job.companies_processed || 0}</td>
                    <td>{job.employees_scraped || 0}</td>
                    <td>
                      <span className={`badge ${job.is_enabled ? 'badge-success' : 'badge-muted'}`}>
                        {job.is_enabled ? 'On' : 'Off'}
                      </span>
                    </td>
                    <td className="text-sm text-muted">
                      {new Date(job.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function StatusBadge({ status }) {
  const styles = {
    pending: 'badge-muted',
    active: 'badge-info',
    processing: 'badge-warning',
    completed: 'badge-success',
    failed: 'badge-danger',
    paused: 'badge-muted',
  }
  return <span className={`badge ${styles[status] || 'badge-muted'}`}>{status}</span>
}

export default Dashboard
