import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getScraperJobs, launchScraperJob, pauseScraperJob } from '../services/api'

function ScraperJobs() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)

  const loadJobs = () => {
    getScraperJobs().then(res => {
      setJobs(res.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }

  useEffect(() => { loadJobs() }, [])

  const handleToggle = async (job) => {
    try {
      if (job.is_enabled) {
        await pauseScraperJob(job.id)
      } else {
        await launchScraperJob(job.id)
      }
      loadJobs()
    } catch (e) {
      alert(e.response?.data?.detail || 'Action failed')
    }
  }

  if (loading) return <div className="text-muted">Loading...</div>

  return (
    <div>
      <div className="page-header">
        <div className="flex justify-between items-center">
          <div>
            <h1>Scraper Jobs</h1>
            <p>Manage your LinkedIn scraping jobs</p>
          </div>
          <Link to="/create" className="btn btn-primary">Create New</Link>
        </div>
      </div>

      {jobs.length === 0 ? (
        <div className="card">
          <p className="text-muted">No scraper jobs yet. Create your first one to get started.</p>
        </div>
      ) : (
        <div className="card">
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Status</th>
                  <th>Companies Found</th>
                  <th>Not Found</th>
                  <th>Employees</th>
                  <th>On/Off</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map(job => (
                  <tr key={job.id}>
                    <td>
                      <Link to={`/scrapers/${job.id}`} style={{ color: 'var(--accent)', textDecoration: 'none' }}>
                        {job.name}
                      </Link>
                    </td>
                    <td><StatusBadge status={job.status} /></td>
                    <td>{job.companies_matched || 0}</td>
                    <td>{job.companies_not_found || 0}</td>
                    <td>{job.employees_scraped || 0}</td>
                    <td>
                      <label className="toggle">
                        <input
                          type="checkbox"
                          checked={job.is_enabled}
                          onChange={() => handleToggle(job)}
                        />
                        <span className="toggle-slider"></span>
                      </label>
                    </td>
                    <td>
                      <Link to={`/scrapers/${job.id}`} className="btn btn-outline btn-sm">
                        View Details
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
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

export default ScraperJobs
