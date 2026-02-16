import React from 'react'
import { Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import CreateScraper from './pages/CreateScraper'
import ScraperJobs from './pages/ScraperJobs'
import JobDetail from './pages/JobDetail'
import LinkedInAccounts from './pages/LinkedInAccounts'

function App() {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-logo">Zavis LinkedIn Tool</div>
        <nav className="sidebar-nav">
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/scrapers">Scraper Jobs</NavLink>
          <NavLink to="/create">Create Scraper</NavLink>
          <NavLink to="/accounts">LinkedIn Accounts</NavLink>
        </nav>
      </aside>
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/scrapers" element={<ScraperJobs />} />
          <Route path="/create" element={<CreateScraper />} />
          <Route path="/scrapers/:id" element={<JobDetail />} />
          <Route path="/accounts" element={<LinkedInAccounts />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
