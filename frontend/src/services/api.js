import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

// Google OAuth
export const getGoogleAuthUrl = () => api.get('/google/auth-url')
export const getGoogleStatus = () => api.get('/google/status')
export const disconnectGoogle = () => api.delete('/google/disconnect')

// LinkedIn Accounts
export const createLinkedInAccount = (data) => api.post('/linkedin-accounts', data)
export const getLinkedInAccounts = () => api.get('/linkedin-accounts')
export const deleteLinkedInAccount = (id) => api.delete(`/linkedin-accounts/${id}`)

// Data Sources
export const createDataSource = (data) => api.post('/data-sources', data)
export const uploadCsvDataSource = (formData) =>
  api.post('/data-sources/upload-csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
export const getDataSources = () => api.get('/data-sources')
export const getDataSourceCompanies = (id) => api.get(`/data-sources/${id}/companies`)

// Google Sheets helpers
export const getSheetTabs = (url) => api.get('/sheets/tabs', { params: { url } })
export const getSheetColumns = (url, tab) =>
  api.get('/sheets/columns', { params: { url, tab } })

// Scraper Jobs
export const createScraperJob = (data) => api.post('/scraper-jobs', data)
export const getScraperJobs = () => api.get('/scraper-jobs')
export const getScraperJob = (id) => api.get(`/scraper-jobs/${id}`)
export const launchScraperJob = (id) => api.post(`/scraper-jobs/${id}/launch`)
export const pauseScraperJob = (id) => api.post(`/scraper-jobs/${id}/pause`)
export const getJobSummary = (id) => api.get(`/scraper-jobs/${id}/summary`)
export const getJobEmployees = (id, matchedOnly = false) =>
  api.get(`/scraper-jobs/${id}/employees`, { params: { matched_only: matchedOnly } })

// AI
export const suggestRoles = (jobTitles, prompt) =>
  api.post('/ai/suggest-roles', { job_titles: jobTitles, prompt })

export default api
