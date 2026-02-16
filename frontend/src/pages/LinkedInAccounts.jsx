import React, { useEffect, useState } from 'react'
import {
  getLinkedInAccounts, createLinkedInAccount, deleteLinkedInAccount,
} from '../services/api'

function LinkedInAccounts() {
  const [accounts, setAccounts] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [loading, setLoading] = useState(true)

  // Form state
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [liAt, setLiAt] = useState('')
  const [jsessionid, setJsessionid] = useState('')
  const [isSalesNav, setIsSalesNav] = useState(true)

  const loadAccounts = () => {
    getLinkedInAccounts().then(res => {
      setAccounts(res.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }

  useEffect(() => { loadAccounts() }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    try {
      await createLinkedInAccount({
        name,
        email: email || undefined,
        li_at_cookie: liAt,
        jsessionid_cookie: jsessionid || undefined,
        is_sales_navigator: isSalesNav,
      })
      setShowForm(false)
      setName('')
      setEmail('')
      setLiAt('')
      setJsessionid('')
      loadAccounts()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to connect account')
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to remove this account?')) return
    await deleteLinkedInAccount(id)
    loadAccounts()
  }

  if (loading) return <div className="text-muted">Loading...</div>

  return (
    <div>
      <div className="page-header">
        <div className="flex justify-between items-center">
          <div>
            <h1>LinkedIn Accounts</h1>
            <p>Manage your connected LinkedIn / Sales Navigator accounts</p>
          </div>
          <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
            {showForm ? 'Cancel' : 'Connect Account'}
          </button>
        </div>
      </div>

      {showForm && (
        <div className="card">
          <h2 className="card-title mb-4">Connect LinkedIn Account</h2>
          <p className="text-sm text-muted mb-4">
            To connect your LinkedIn account, you need to provide your authentication cookies.
            Log into LinkedIn in your browser, then extract the <code>li_at</code> and <code>JSESSIONID</code> cookies
            from your browser's developer tools (Application &gt; Cookies &gt; linkedin.com).
          </p>
          <form onSubmit={handleCreate}>
            <div className="form-group">
              <label>Account Name</label>
              <input className="form-input" value={name} onChange={e => setName(e.target.value)} placeholder="e.g. My Sales Navigator" required />
            </div>
            <div className="form-group">
              <label>Email (optional)</label>
              <input className="form-input" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="your@email.com" />
            </div>
            <div className="form-group">
              <label>li_at Cookie (required)</label>
              <textarea className="form-textarea" value={liAt} onChange={e => setLiAt(e.target.value)} placeholder="Paste your li_at cookie value here" required />
            </div>
            <div className="form-group">
              <label>JSESSIONID Cookie (optional but recommended)</label>
              <input className="form-input" value={jsessionid} onChange={e => setJsessionid(e.target.value)} placeholder="Paste JSESSIONID value" />
            </div>
            <div className="form-group">
              <label className="flex items-center gap-2">
                <label className="toggle">
                  <input type="checkbox" checked={isSalesNav} onChange={e => setIsSalesNav(e.target.checked)} />
                  <span className="toggle-slider"></span>
                </label>
                Sales Navigator Account
              </label>
            </div>
            <button className="btn btn-success" type="submit">Connect Account</button>
          </form>
        </div>
      )}

      <div className="card">
        {accounts.length === 0 ? (
          <p className="text-muted">No LinkedIn accounts connected. Click "Connect Account" to add one.</p>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Connected</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map(acc => (
                  <tr key={acc.id}>
                    <td>{acc.name}</td>
                    <td>{acc.email || '-'}</td>
                    <td>
                      <span className={`badge ${acc.is_sales_navigator ? 'badge-info' : 'badge-muted'}`}>
                        {acc.is_sales_navigator ? 'Sales Navigator' : 'Standard'}
                      </span>
                    </td>
                    <td><span className="badge badge-success">{acc.status}</span></td>
                    <td className="text-sm text-muted">{new Date(acc.connected_at).toLocaleDateString()}</td>
                    <td>
                      <button className="btn btn-danger btn-sm" onClick={() => handleDelete(acc.id)}>Remove</button>
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

export default LinkedInAccounts
