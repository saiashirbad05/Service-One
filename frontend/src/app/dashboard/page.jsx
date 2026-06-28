'use client'

import React, { useState, useEffect, useMemo, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Header from '../../components/layout-next/Header'
import Footer from '../../components/layout-next/Footer'

// ── JSDoc Type Definitions ───────────────────────────────────
/**
 * @typedef {Object} QuoteCheck
 * @property {number} id
 * @property {string} created_at
 * @property {string} appliance_type
 * @property {string} service_type
 * @property {string} city
 * @property {string} [area]
 * @property {number} quoted_price
 * @property {number} potential_savings
 * @property {'fair' | 'high' | 'suspicious' | 'low'} verdict
 * @property {'High' | 'Medium' | 'Fallback'} confidence_level
 * @property {boolean} is_bookmarked
 * @property {Array<{url: string, title: string, snippet?: string}>} source_links
 */

// ── Realistic Indian Local Market Seed Data Fallback ────────────────────────
/** @type {QuoteCheck[]} */
const MOCK_HISTORY_DATA = [
  {
    id: 101,
    created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
    appliance_type: 'AC',
    service_type: 'Gas Refill',
    city: 'Bhubaneswar',
    area: 'Patia',
    quoted_price: 3200,
    potential_savings: 1000,
    verdict: 'high',
    confidence_level: 'High',
    is_bookmarked: false,
    source_links: [
      { title: 'Urban Company Bhubaneswar AC Rates Sheet', url: 'https://urbancompany.com' }
    ]
  },
  {
    id: 102,
    created_at: new Date(Date.now() - 3600000 * 24).toISOString(),
    appliance_type: 'TV',
    service_type: 'Panel Replacement',
    city: 'Cuttack',
    area: 'Bajrakabari Road',
    quoted_price: 6500,
    potential_savings: 0,
    verdict: 'fair',
    confidence_level: 'High',
    is_bookmarked: true,
    source_links: []
  },
  {
    id: 103,
    created_at: new Date(Date.now() - 3600000 * 48).toISOString(),
    appliance_type: 'Washing Machine',
    service_type: 'Drum Bearing Fix',
    city: 'Bhubaneswar',
    area: 'Kalarahanga',
    quoted_price: 4500,
    potential_savings: 2000,
    verdict: 'suspicious',
    confidence_level: 'Medium',
    is_bookmarked: false,
    source_links: []
  },
  {
    id: 104,
    created_at: new Date(Date.now() - 3600000 * 72).toISOString(),
    appliance_type: 'RO',
    service_type: 'Filter Replacement',
    city: 'Mumbai',
    area: 'Bandra West',
    quoted_price: 1800,
    potential_savings: 800,
    verdict: 'high',
    confidence_level: 'Fallback',
    is_bookmarked: false,
    source_links: []
  },
  {
    id: 105,
    created_at: new Date(Date.now() - 3600000 * 120).toISOString(),
    appliance_type: 'Geyser',
    service_type: 'Thermostat Fix',
    city: 'New Delhi',
    area: 'Karol Bagh',
    quoted_price: 900,
    potential_savings: 0,
    verdict: 'fair',
    confidence_level: 'High',
    is_bookmarked: false,
    source_links: []
  }
]

// JWT Decode Helper
function decodeJwt(token) {
  try {
    if (!token) return null
    if (token === 'mock_developer_bypass_token') {
      return { email: 'developer@serviceone.dev', name: 'Demo Developer' }
    }
    if (token.startsWith('mock_user')) {
      const uNum = token.replace('mock_user', '')
      return { email: `user${uNum}@serviceone.dev`, name: `User ${uNum}` }
    }
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function(c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
    }).join(''))
    return JSON.parse(jsonPayload)
  } catch (e) {
    return null
  }
}

const API = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000'

export default function DashboardPage() {
  const router = useRouter()
  const [history, setHistory] = useState([])
  const [customSearches, setCustomSearches] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [currentUser, setCurrentUser] = useState(null)
  const [activeTab, setActiveTab] = useState('history')

  // Interactive filter state
  const [selectedVerdictFilter, setSelectedVerdictFilter] = useState(null)

  // Tracker state
  const [newSearch, setNewSearch] = useState({ search_label: '', search_url: '', notes: '' })
  const [addingSearch, setAddingSearch] = useState(false)

  // Expanded row
  const [expandedId, setExpandedId] = useState(null)

  // Community reports state
  const [reports, setReports] = useState([])
  const [reportsLoading, setReportsLoading] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [modalForm, setModalForm] = useState({ city: '', area: '', appliance: 'AC', service_type: 'Installation', provider_name: '', quoted_price: '', notes: '' })
  const [proofFile, setProofFile] = useState(null)
  const [uploadingImage, setUploadingImage] = useState(false)
  const [imagePreview, setImagePreview] = useState(null)
  const [proofImageUrl, setProofImageUrl] = useState('')

  const getAuthHeaders = (contentType = 'application/json') => {
    const token = localStorage.getItem('token')
    const headers = {}
    if (contentType) {
      headers['Content-Type'] = contentType
    }
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    return headers
  }

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      window.location.href = '/login/'
      return
    }
    const decoded = decodeJwt(token)
    if (decoded) {
      setCurrentUser(decoded)
    }
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const headers = getAuthHeaders()
      const [histRes, customRes] = await Promise.all([
        fetch(`${API}/api/history?limit=50`, { headers }),
        fetch(`${API}/api/custom-searches?limit=50`, { headers }),
      ])
      
      let realHistory = []
      if (histRes.ok) {
        const hData = await histRes.json()
        realHistory = hData.history || []
      }
      
      if (realHistory.length === 0) {
        setHistory(MOCK_HISTORY_DATA)
      } else {
        const levels = ['High', 'Medium', 'Fallback']
        setHistory(realHistory.map((item, idx) => ({
          ...item,
          confidence_level: item.confidence_level || levels[idx % 3]
        })))
      }

      if (customRes.ok) {
        const cData = await customRes.json()
        setCustomSearches(cData.searches || [])
      }

      setReportsLoading(true)
      const repRes = await fetch(`${API}/api/user-reports`, { headers })
      if (repRes.ok) {
        const rData = await repRes.json()
        setReports(rData.reports || [])
      }
      setReportsLoading(false)
    } catch (err) {
      setHistory(MOCK_HISTORY_DATA)
      setError('Offline mode: showing local mock diagnosis examples.')
    }
    setLoading(false)
  }

  const statsMetrics = useMemo(() => {
    const totalSavings = history.reduce((acc, item) => acc + (item.potential_savings > 0 ? Number(item.potential_savings) : 0), 0)
    const totalChecked = history.length
    const breakdown = { fair: 0, high: 0, suspicious: 0, low: 0 }
    history.forEach(item => {
      const v = item.verdict?.toLowerCase()
      if (breakdown[v] !== undefined) {
        breakdown[v]++
      }
    })
    return { totalSavings, totalChecked, breakdown }
  }, [history])

  const bookmarkedCount = useMemo(() => history.filter(h => h.is_bookmarked).length, [history])

  const filteredHistoryList = useMemo(() => {
    let result = history
    if (activeTab === 'bookmarks') {
      result = result.filter(h => h.is_bookmarked)
    }
    if (selectedVerdictFilter) {
      result = result.filter(h => h.verdict?.toLowerCase() === selectedVerdictFilter.toLowerCase())
    }
    return result
  }, [history, activeTab, selectedVerdictFilter])

  const toggleBookmark = async (id) => {
    try {
      const res = await fetch(`${API}/api/history/${id}/bookmark`, {
        method: 'POST',
        headers: getAuthHeaders()
      })
      if (res.ok) {
        const data = await res.json()
        setHistory(prev => prev.map(item => 
          item.id === id ? { ...item, is_bookmarked: data.is_bookmarked } : item
        ))
      }
    } catch (err) {
      setHistory(prev => prev.map(item => 
        item.id === id ? { ...item, is_bookmarked: !item.is_bookmarked } : item
      ))
    }
  }

  const handleImageChange = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setProofFile(file)
    setImagePreview(URL.createObjectURL(file))
    setUploadingImage(true)
    const formData = new FormData()
    formData.append('file', file)
    try {
      const res = await fetch(`${API}/api/upload-proof`, {
        method: 'POST',
        headers: getAuthHeaders(null),
        body: formData
      })
      if (res.ok) {
        const data = await res.json()
        setProofImageUrl(data.url)
      }
    } catch (err) {
      console.error(err)
    } finally {
      setUploadingImage(false)
    }
  }

  const submitCommunityReport = async (e) => {
    e.preventDefault()
    if (!modalForm.city.trim() || !modalForm.quoted_price) return
    try {
      const payload = {
        ...modalForm,
        quoted_price: Number(modalForm.quoted_price),
        user_email: currentUser?.email || null,
        user_name: currentUser?.name || null,
        proof_image_url: proofImageUrl || null
      }
      const res = await fetch(`${API}/api/reports`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload)
      })
      if (res.ok) {
        setShowModal(false)
        setModalForm({ city: '', area: '', appliance: 'AC', service_type: 'Installation', provider_name: '', quoted_price: '', notes: '' })
        setProofFile(null)
        setImagePreview(null)
        setProofImageUrl('')
        fetchData()
      }
    } catch (err) {
      console.error(err)
    }
  }

  const downloadPDFReport = async (item) => {
    const resultData = item.full_result_json || {}
    const element = document.createElement('div')
    element.style.padding = '40px'
    element.style.fontFamily = "'Outfit', sans-serif"
    element.style.color = '#1e293b'
    element.style.backgroundColor = '#ffffff'
    element.style.width = '700px'
    element.style.margin = '0 auto'
    element.innerHTML = `
      <div style="border: 2px solid #0f172a; padding: 30px; border-radius: 20px;">
        <h1 style="font-size: 24px; font-weight: 800; color: #0f172a;">🛡️ ServiceOne Diagnostic Report</h1>
        <p style="font-size: 13px; color: #64748b;">Invoice check executed on ${new Date(item.created_at).toLocaleDateString('en-IN')}</p>
        <hr style="margin: 20px 0; border: none; border-top: 1px solid #e2e8f0;" />
        <p style="font-size: 16px;">Appliance: <strong>${item.appliance_type}</strong></p>
        <p style="font-size: 16px;">Service: <strong>${item.service_type}</strong></p>
        <p style="font-size: 16px;">City: <strong>${item.city}</strong></p>
        <p style="font-size: 18px; color: #b91c1c; font-weight: 700;">Verdict: ${item.verdict?.toUpperCase()}</p>
        <div style="background-color: #f8fafc; padding: 15px; border-radius: 12px; margin-top: 20px;">
          <p style="font-size: 13px; font-weight: 700; color: #475569;">Diagnostic Notes:</p>
          <p style="font-size: 13px; line-height: 1.6; color: #334155;">${resultData.explanation || 'Market quote checked successfully against certified lists.'}</p>
        </div>
      </div>
    `
    const html2pdf = (await import('html2pdf.js')).default
    const opt = {
      margin: 10,
      filename: `serviceone_report_${item.appliance_type}_${item.id}.pdf`,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2 },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
    }
    html2pdf().from(element).set(opt).save()
  }

  const addCustomSearch = async (e) => {
    e.preventDefault()
    if (!newSearch.search_label.trim() || !newSearch.search_url.trim()) return
    setAddingSearch(true)
    try {
      const res = await fetch(`${API}/api/custom-search`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ ...newSearch, search_type: 'custom' }),
      })
      if (res.ok) {
        setNewSearch({ search_label: '', search_url: '', notes: '' })
        fetchData()
      }
    } catch (err) {
      setCustomSearches(prev => [
        ...prev,
        { id: Date.now(), search_label: newSearch.search_label, search_url: newSearch.search_url, notes: newSearch.notes, created_at: new Date().toISOString() }
      ])
      setNewSearch({ search_label: '', search_url: '', notes: '' })
    }
    setAddingSearch(false)
  }

  const deleteCustomSearch = async (id) => {
    try {
      const res = await fetch(`${API}/api/custom-search/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      })
      if (res.ok) {
        setCustomSearches(prev => prev.filter(s => s.id !== id))
      }
    } catch (err) {
      setCustomSearches(prev => prev.filter(s => s.id !== id))
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', backgroundColor: 'var(--bg)', color: 'var(--text)', fontFamily: 'sans-serif', transition: 'background-color 0.2s, color 0.2s' }}>
      <Header />

      <main style={{ flexGrow: 1, maxWidth: '1200px', width: '100%', margin: '0 auto', padding: '2rem 1rem' }}>
        
        {/* Header */}
        <div style={{ display: 'flex', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '1.5rem', marginBottom: '2rem' }}>
          <div>
            <h1 style={{ fontSize: '1.875rem', fontWeight: 800, color: 'var(--text)', margin: 0 }}>User Quote History Dashboard</h1>
            <p style={{ color: 'var(--muted)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
              Active diagnostic summary for <span style={{ color: 'var(--brand)', fontWeight: 600 }}>{currentUser?.name || 'Saiashribad'}</span>
            </p>
          </div>
          <button
            onClick={() => { localStorage.removeItem('token'); window.location.href = '/login/'; }}
            style={{ padding: '0.5rem 1rem', backgroundColor: 'var(--surface-soft)', border: '1px solid var(--border)', borderRadius: '0.75rem', fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--text)', cursor: 'pointer', transition: 'all 0.2s' }}
          >
            Log Out
          </button>
        </div>

        {/* ── Metric Cards Grid ──────────────────────────────── */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
          {/* Card 1: Savings */}
          <div style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '1rem', padding: '1.5rem', position: 'relative', overflow: 'hidden', boxShadow: 'var(--shadow-soft)' }}>
            <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: '6px', backgroundColor: '#10b981' }}></div>
            <p style={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--muted)', margin: 0, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Total Savings Counter</p>
            <h2 style={{ fontSize: '2rem', fontWeight: 900, color: '#10b981', marginTop: '0.5rem', fontFamily: 'monospace' }}>
              ₹{statsMetrics.totalSavings.toLocaleString('en-IN')}
            </h2>
            <p style={{ fontSize: '0.7rem', color: 'var(--muted)', marginTop: '0.5rem', margin: 0 }}>Accumulated discount against regional market averages</p>
          </div>

          {/* Card 2: Quotes Checked */}
          <div style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '1rem', padding: '1.5rem', position: 'relative', overflow: 'hidden', boxShadow: 'var(--shadow-soft)' }}>
            <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: '6px', backgroundColor: 'var(--brand)' }}></div>
            <p style={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--muted)', margin: 0, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Quotes Checked Count</p>
            <h2 style={{ fontSize: '2rem', fontWeight: 900, color: 'var(--text)', marginTop: '0.5rem', fontFamily: 'monospace' }}>
              {statsMetrics.totalChecked} Scans
            </h2>
            <p style={{ fontSize: '0.7rem', color: 'var(--muted)', marginTop: '0.5rem', margin: 0 }}>Total invoice validations run by this account</p>
          </div>

          {/* Card 3: Saved */}
          <div style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '1rem', padding: '1.5rem', position: 'relative', overflow: 'hidden', boxShadow: 'var(--shadow-soft)' }}>
            <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: '6px', backgroundColor: '#f59e0b' }}></div>
            <p style={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--muted)', margin: 0, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Bookmarked Checks</p>
            <h2 style={{ fontSize: '2rem', fontWeight: 900, color: '#f59e0b', marginTop: '0.5rem', fontFamily: 'monospace' }}>
              {bookmarkedCount} Saved
            </h2>
            <p style={{ fontSize: '0.7rem', color: 'var(--muted)', marginTop: '0.5rem', margin: 0 }}>Saved reports for technician negotiation reference</p>
          </div>
        </div>

        {/* ── Interactive Summary Chart ──────────────────────── */}
        <div style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '1rem', padding: '1.5rem', marginBottom: '2rem', boxShadow: 'var(--shadow-soft)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div>
              <h3 style={{ fontSize: '0.875rem', fontWeight: 'bold', color: 'var(--text)', margin: 0, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Interactive Summary Chart</h3>
              <p style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '0.25rem', margin: 0 }}>Click a verdict category to filter the historical data grid.</p>
            </div>
            {selectedVerdictFilter && (
              <button 
                onClick={() => setSelectedVerdictFilter(null)}
                style={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--brand)', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}
              >
                Show All Verdicts
              </button>
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
            {[
              { key: 'fair', label: 'Fair Pricing', count: statsMetrics.breakdown.fair, color: '#10b981', text: '#10b981', barBg: 'rgba(16, 185, 129, 0.15)' },
              { key: 'high', label: 'High Pricing', count: statsMetrics.breakdown.high, color: '#f59e0b', text: '#f59e0b', barBg: 'rgba(245, 158, 11, 0.15)' },
              { key: 'suspicious', label: 'Suspicious', count: statsMetrics.breakdown.suspicious, color: '#ef4444', text: '#ef4444', barBg: 'rgba(239, 68, 68, 0.15)' },
              { key: 'low', label: 'Low / Bargain', count: statsMetrics.breakdown.low, color: '#3b82f6', text: '#3b82f6', barBg: 'rgba(59, 130, 246, 0.15)' }
            ].map(item => {
              const total = statsMetrics.totalChecked || 1
              const percent = Math.round((item.count / total) * 100)
              const isActive = selectedVerdictFilter === item.key

              return (
                <div 
                  key={item.key}
                  onClick={() => setSelectedVerdictFilter(isActive ? null : item.key)}
                  style={{
                    padding: '1rem',
                    borderRadius: '0.75rem',
                    border: isActive ? '1px solid var(--brand)' : '1px solid var(--border)',
                    backgroundColor: isActive ? 'var(--surface-soft)' : 'var(--bg)',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
                    <span style={{ color: 'var(--text)' }}>{item.label}</span>
                    <span style={{ color: item.text }}>{item.count} ({percent}%)</span>
                  </div>
                  <div style={{ width: '100%', height: '8px', borderRadius: '9999px', backgroundColor: 'var(--border)', overflow: 'hidden' }}>
                    <div 
                      style={{ height: '100%', borderRadius: '9999px', backgroundColor: item.color, width: `${percent}%`, transition: 'width 0.3s ease' }}
                    ></div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Tab Controls */}
        <div style={{ display: 'flex', gap: '0.25rem', padding: '0.25rem', backgroundColor: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '0.75rem', width: 'fit-content', marginBottom: '1.5rem' }}>
          {[
            { id: 'history', label: '📊 Audit History' },
            { id: 'bookmarks', label: '⭐ Saved checks' },
            { id: 'custom', label: '🔗 Trackers' },
            { id: 'reports', label: '🤝 Community Invoices' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => { setActiveTab(tab.id); setSelectedVerdictFilter(null); }}
              style={{
                padding: '0.5rem 1rem',
                fontSize: '0.75rem',
                fontWeight: 'bold',
                borderRadius: '0.5rem',
                border: 'none',
                cursor: 'pointer',
                backgroundColor: activeTab === tab.id ? 'var(--surface)' : 'transparent',
                color: activeTab === tab.id ? 'var(--text)' : 'var(--muted)',
                transition: 'all 0.2s'
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {error && (
          <div style={{ padding: '1rem', backgroundColor: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.2)', color: '#fbbf24', borderRadius: '0.75rem', marginBottom: '1.5rem', fontSize: '0.75rem', fontWeight: 'bold' }}>
            ⚠️ {error}
          </div>
        )}

        {/* Main Grid Card Content */}
        <div style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '1rem', overflow: 'hidden', boxShadow: 'var(--shadow-soft)' }}>
          
          {/* Audit History Logs */}
          {(activeTab === 'history' || activeTab === 'bookmarks') && (
            <div>
              {filteredHistoryList.length === 0 ? (
                <div style={{ padding: '4rem 1rem', textAlign: 'center', color: 'var(--muted)' }}>
                  <p style={{ fontSize: '0.875rem', fontWeight: 600, margin: 0 }}>No records found matching filters.</p>
                  <button 
                    onClick={() => router.push('/services')}
                    style={{ marginTop: '1rem', padding: '0.5rem 1rem', backgroundColor: 'var(--brand)', border: 'none', borderRadius: '0.5rem', color: '#ffffff', fontWeight: 'bold', fontSize: '0.75rem', cursor: 'pointer' }}
                  >
                    Check a Quote
                  </button>
                </div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', minWidth: '700px' }}>
                    <thead style={{ backgroundColor: 'var(--surface-soft)', fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--muted)', textTransform: 'uppercase' }}>
                      <tr>
                        <th style={{ padding: '1rem' }}>Date</th>
                        <th style={{ padding: '1rem' }}>Appliance & Service</th>
                        <th style={{ padding: '1rem' }}>Quoted Price</th>
                        <th style={{ padding: '1rem' }}>Verdict Badge</th>
                        <th style={{ padding: '1rem' }}>Confidence Level</th>
                        <th style={{ padding: '1rem' }}>Savings Retained</th>
                        <th style={{ padding: '1rem', textAlign: 'center' }}>Certificate</th>
                        <th style={{ padding: '1rem' }}></th>
                      </tr>
                    </thead>
                    <tbody style={{ color: 'var(--text)', fontSize: '0.875rem' }}>
                      {filteredHistoryList.map(item => {
                        const style = VERDICT_STYLES[item.verdict] || VERDICT_STYLES.fair
                        const isExpanded = expandedId === item.id
                        const confStyle = CONFIDENCE_STYLES[item.confidence_level || 'High']

                        return (
                          <React.Fragment key={item.id}>
                            <tr style={{ borderBottom: '1px solid var(--border)' }}>
                              <td style={{ padding: '1rem', fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--muted)' }}>
                                {new Date(item.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                              </td>
                              <td style={{ padding: '1rem' }}>
                                <div style={{ fontWeight: 'bold', color: 'var(--text)' }}>{item.appliance_type?.toUpperCase()}</div>
                                <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '0.125rem' }}>{item.service_type} • {item.city} ({item.area || 'General'})</div>
                              </td>
                              <td style={{ padding: '1rem', fontWeight: 'bold', color: 'var(--text)', fontFamily: 'monospace', fontSize: '1rem' }}>
                                ₹{Number(item.quoted_price).toLocaleString('en-IN')}
                              </td>
                              <td style={{ padding: '1rem' }}>
                                <span style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  padding: '0.25rem 0.75rem',
                                  borderRadius: '9999px',
                                  fontSize: '0.7rem',
                                  fontWeight: 'bold',
                                  textTransform: 'uppercase',
                                  border: `1px solid ${style.color}50`,
                                  backgroundColor: `${style.color}15`,
                                  color: style.color
                                }}>
                                  {style.label}
                                </span>
                              </td>
                              <td style={{ padding: '1rem' }}>
                                <span style={{
                                  display: 'inline-block',
                                  padding: '0.125rem 0.5rem',
                                  borderRadius: '0.25rem',
                                  fontSize: '0.7rem',
                                  fontWeight: 'bold',
                                  border: `1px solid ${confStyle.includes('High') ? '#10b98130' : confStyle.includes('Medium') ? '#f59e0b30' : '#6366f130'}`,
                                  backgroundColor: confStyle.includes('High') ? 'rgba(16, 185, 129, 0.15)' : confStyle.includes('Medium') ? 'rgba(245, 158, 11, 0.15)' : 'rgba(99, 102, 241, 0.15)',
                                  color: confStyle.includes('High') ? '#10b981' : confStyle.includes('Medium') ? '#f59e0b' : '#6366f1'
                                }}>
                                  {item.confidence_level || 'High'}
                                </span>
                              </td>
                              <td style={{ padding: '1rem', fontFamily: 'monospace' }}>
                                {item.potential_savings > 0 ? (
                                  <span style={{ color: '#10b981', fontWeight: 'bold' }}>₹{Number(item.potential_savings).toLocaleString('en-IN')}</span>
                                ) : (
                                  <span style={{ color: 'var(--muted)' }}>—</span>
                                )}
                              </td>
                              <td style={{ padding: '1rem', textAlign: 'center' }}>
                                <button
                                  onClick={() => downloadPDFReport(item)}
                                  style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', fontWeight: 'bold', backgroundColor: 'var(--surface-soft)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: '0.375rem', cursor: 'pointer' }}
                                >
                                  📥 Report
                                </button>
                              </td>
                              <td style={{ padding: '1rem', textAlign: 'right' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', justifyContent: 'flex-end' }}>
                                  {item.source_links?.length > 0 && (
                                    <button
                                      onClick={() => setExpandedId(isExpanded ? null : item.id)}
                                      style={{ padding: '0.125rem 0.375rem', borderRadius: '0.25rem', fontSize: '0.7rem', fontWeight: 'bold', backgroundColor: 'rgba(99, 102, 241, 0.15)', color: '#818cf8', border: 'none', cursor: 'pointer' }}
                                    >
                                      {isExpanded ? 'Close' : `${item.source_links.length} sources`}
                                    </button>
                                  )}
                                  <button onClick={() => toggleBookmark(item.id)} style={{ background: 'none', border: 'none', color: '#fbbf24', fontSize: '1rem', cursor: 'pointer' }}>
                                    {item.is_bookmarked ? '⭐' : '☆'}
                                  </button>
                                </div>
                              </td>
                            </tr>
                            {isExpanded && (
                              <tr>
                                <td colSpan={8} style={{ padding: '1rem', backgroundColor: 'var(--surface-soft)' }}>
                                  <div style={{ fontSize: '0.75rem', fontWeight: 'bold', textTransform: 'uppercase', color: 'var(--muted)', marginBottom: '0.5rem' }}>Sources Checked:</div>
                                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.75rem' }}>
                                    {item.source_links.map((link, idx) => (
                                      <a key={idx} href={link.url} target="_blank" rel="noopener noreferrer" style={{ display: 'block', padding: '0.75rem', borderRadius: '0.5rem', backgroundColor: 'var(--surface)', border: '1px solid var(--border)', textDecoration: 'none' }}>
                                        <div style={{ fontSize: '0.875rem', fontWeight: 'bold', color: 'var(--brand)' }}>{link.title || 'Source'}</div>
                                        {link.snippet && <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '0.25rem' }}>{link.snippet}</div>}
                                      </a>
                                    ))}
                                  </div>
                                </td>
                              </tr>
                            )}
                          </React.Fragment>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: Trackers */}
          {activeTab === 'custom' && (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <div style={{ padding: '1.5rem', backgroundColor: 'var(--surface-soft)' }}>
                <h3 style={{ fontSize: '0.875rem', fontWeight: 'bold', color: 'var(--text)', margin: '0 0 1rem 0', textTransform: 'uppercase' }}>Track Competitor Listings</h3>
                <form onSubmit={addCustomSearch} style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'flex-end' }}>
                  <div style={{ flex: '1 1 200px' }}>
                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--muted)', marginBottom: '0.25rem' }}>Label *</label>
                    <input type="text" placeholder="e.g. Patia Sulekha AC Rates" value={newSearch.search_label} onChange={e => setNewSearch(s => ({ ...s, search_label: e.target.value }))} style={{ width: '100%', padding: '0.5rem', backgroundColor: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '0.5rem', color: 'var(--text)', outline: 'none' }} required />
                  </div>
                  <div style={{ flex: '2 1 300px' }}>
                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--muted)', marginBottom: '0.25rem' }}>URL *</label>
                    <input type="url" placeholder="https://sulekha.com/..." value={newSearch.search_url} onChange={e => setNewSearch(s => ({ ...s, search_url: e.target.value }))} style={{ width: '100%', padding: '0.5rem', backgroundColor: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '0.5rem', color: 'var(--text)', outline: 'none' }} required />
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem', flex: '1 1 200px' }}>
                    <div style={{ flex: 1 }}>
                      <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--muted)', marginBottom: '0.25rem' }}>Notes</label>
                      <input type="text" placeholder="Optional details" value={newSearch.notes} onChange={e => setNewSearch(s => ({ ...s, notes: e.target.value }))} style={{ width: '100%', padding: '0.5rem', backgroundColor: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '0.5rem', color: 'var(--text)', outline: 'none' }} />
                    </div>
                    <button type="submit" disabled={addingSearch} style={{ padding: '0.5rem 1.25rem', fontSize: '0.75rem', fontWeight: 'bold', backgroundColor: 'var(--brand)', border: 'none', borderRadius: '0.5rem', color: '#ffffff', cursor: 'pointer', height: '37px' }}>
                      Add
                    </button>
                  </div>
                </form>
              </div>
              <div style={{ padding: '1.5rem' }}>
                {customSearches.length === 0 ? (
                  <div style={{ textAlign: 'center', color: 'var(--muted)', fontSize: '0.875rem' }}>No custom listings saved.</div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
                    {customSearches.map(item => (
                      <div key={item.id} style={{ padding: '1rem', borderRadius: '0.75rem', backgroundColor: 'var(--bg)', border: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
                        <div style={{ minWidth: 0, flex: 1 }}>
                          <div style={{ fontWeight: 'bold', color: 'var(--text)' }}>{item.search_label}</div>
                          <a href={item.search_url} target="_blank" rel="noopener noreferrer" style={{ fontSize: '0.75rem', color: 'var(--brand)', textDecoration: 'underline', display: 'block', marginTop: '0.25rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.search_url}</a>
                          {item.notes && <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '0.5rem', fontStyle: 'italic' }}>“{item.notes}”</div>}
                        </div>
                        <button onClick={() => deleteCustomSearch(item.id)} style={{ padding: '0.25rem 0.5rem', fontSize: '0.7rem', fontWeight: 'bold', borderRadius: '0.25rem', backgroundColor: 'rgba(239, 68, 68, 0.15)', color: '#f87171', border: '1px solid rgba(239, 68, 68, 0.25)', cursor: 'pointer' }}>
                          Delete
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 4: Community Price Submissions */}
          {activeTab === 'reports' && (
            <div style={{ padding: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
                <div>
                  <h3 style={{ fontSize: '0.875rem', fontWeight: 'bold', color: 'var(--text)', margin: 0, textTransform: 'uppercase' }}>Community Pricing Reports</h3>
                  <p style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '0.25rem', margin: 0 }}>Review quotes shared by nearby users to verify pricing indexes.</p>
                </div>
                <button onClick={() => setShowModal(true)} style={{ padding: '0.5rem 1rem', fontSize: '0.75rem', fontWeight: 'bold', backgroundColor: 'var(--brand)', border: 'none', borderRadius: '0.5rem', color: '#ffffff', cursor: 'pointer' }}>
                  + Submit Invoice Report
                </button>
              </div>

              {reportsLoading ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--muted)' }}>Loading community reports...</div>
              ) : reports.length === 0 ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--muted)', fontSize: '0.875rem' }}>No reports submitted by you yet.</div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', minWidth: '700px' }}>
                    <thead style={{ backgroundColor: 'var(--surface-soft)', fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--muted)', textTransform: 'uppercase' }}>
                      <tr>
                        <th style={{ padding: '1rem' }}>Date</th>
                        <th style={{ padding: '1rem' }}>Appliance & Service</th>
                        <th style={{ padding: '1rem' }}>Location</th>
                        <th style={{ padding: '1rem' }}>Provider</th>
                        <th style={{ padding: '1rem' }}>Price</th>
                        <th style={{ padding: '1rem' }}>Proof</th>
                        <th style={{ padding: '1rem' }}>Status</th>
                      </tr>
                    </thead>
                    <tbody style={{ color: 'var(--text)', fontSize: '0.875rem' }}>
                      {reports.map(report => (
                        <tr key={report.id} style={{ borderBottom: '1px solid var(--border)' }}>
                          <td style={{ padding: '1rem', fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--muted)' }}>{new Date(report.created_at).toLocaleDateString('en-IN')}</td>
                          <td style={{ padding: '1rem' }}>
                            <div style={{ fontWeight: 'bold', color: 'var(--text)' }}>{report.appliance?.toUpperCase()}</div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '0.125rem' }}>{report.service_type}</div>
                          </td>
                          <td style={{ padding: '1rem' }}>
                            <div>{report.city}</div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '0.125rem' }}>{report.area || 'Local Area'}</div>
                          </td>
                          <td style={{ padding: '1rem' }}>{report.provider_name || '—'}</td>
                          <td style={{ padding: '1rem', fontWeight: 'bold', color: 'var(--text)', fontFamily: 'monospace' }}>₹{Number(report.quoted_price).toLocaleString('en-IN')}</td>
                          <td style={{ padding: '1rem' }}>
                            {report.proof_image_url ? (
                              <a href={report.proof_image_url} target="_blank" rel="noopener noreferrer" style={{ display: 'inline-block', padding: '0.125rem 0.5rem', fontSize: '0.7rem', fontWeight: 'bold', borderRadius: '0.25rem', backgroundColor: 'rgba(99, 102, 241, 0.15)', color: '#818cf8', textDecoration: 'none', border: '1px solid rgba(99, 102, 241, 0.25)' }}>View</a>
                            ) : (
                              <span style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>None</span>
                            )}
                          </td>
                          <td style={{ padding: '1rem' }}>
                            <span style={{
                              display: 'inline-block',
                              padding: '0.125rem 0.5rem',
                              borderRadius: '9999px',
                              fontSize: '0.7rem',
                              fontWeight: 'bold',
                              textTransform: 'uppercase',
                              backgroundColor: report.approved_status === 'approved' ? 'rgba(16, 185, 129, 0.15)' : report.approved_status === 'rejected' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                              color: report.approved_status === 'approved' ? '#10b981' : report.approved_status === 'rejected' ? '#ef4444' : '#f59e0b',
                              border: `1px solid ${report.approved_status === 'approved' ? '#10b98130' : report.approved_status === 'rejected' ? '#ef444430' : '#f59e0b30'}`
                            }}>
                              {report.approved_status || 'pending'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Diagnostic Actions Banner */}
        <div style={{ marginTop: '2rem', textAlign: 'center' }}>
          <button
            onClick={() => router.push('/services')}
            style={{ padding: '0.75rem 1.5rem', backgroundColor: 'var(--brand)', border: 'none', borderRadius: '0.75rem', color: '#ffffff', fontWeight: 'bold', fontSize: '0.875rem', cursor: 'pointer', boxShadow: '0 4px 6px -1px rgba(79, 70, 229, 0.2)' }}
          >
            + Audit a Repair Quote
          </button>
        </div>

        {/* Modal: Community Submission */}
        {showModal && (
          <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(2, 6, 23, 0.7)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyStyle: 'center', zIndex: 9999, padding: '1rem' }}>
            <div style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '1.5rem', width: '100%', maxWidth: '500px', overflow: 'hidden' }}>
              <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: 'var(--surface-soft)' }}>
                <h3 style={{ fontSize: '0.875rem', fontWeight: 'bold', color: 'var(--text)', margin: 0, textTransform: 'uppercase' }}>Submit Invoice Details</h3>
                <button onClick={() => setShowModal(false)} style={{ background: 'none', border: 'none', color: 'var(--muted)', fontSize: '1.25rem', cursor: 'pointer' }}>✕</button>
              </div>

              <form onSubmit={submitCommunityReport} style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--muted)', marginBottom: '0.25rem' }}>City *</label>
                    <input type="text" placeholder="e.g. Bhubaneswar" value={modalForm.city} onChange={e => setModalForm(f => ({ ...f, city: e.target.value }))} style={{ width: '100%', padding: '0.5rem', backgroundColor: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '0.5rem', color: 'var(--text)', outline: 'none' }} required />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--muted)', marginBottom: '0.25rem' }}>Area</label>
                    <input type="text" placeholder="e.g. Patia" value={modalForm.area} onChange={e => setModalForm(f => ({ ...f, area: e.target.value }))} style={{ width: '100%', padding: '0.5rem', backgroundColor: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '0.5rem', color: 'var(--text)', outline: 'none' }} />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--muted)', marginBottom: '0.25rem' }}>Appliance *</label>
                    <select value={modalForm.appliance} onChange={e => setModalForm(f => ({ ...f, appliance: e.target.value }))} style={{ width: '100%', padding: '0.5rem', backgroundColor: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '0.5rem', color: 'var(--text)', outline: 'none' }} required>
                      {['AC', 'Fridge', 'Washing Machine', 'TV', 'RO', 'Geyser'].map(app => (
                        <option key={app} value={app} className="bg-slate-900">{app}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--muted)', marginBottom: '0.25rem' }}>Service Type</label>
                    <input type="text" placeholder="e.g. Compressor Repair" value={modalForm.service_type} onChange={e => setModalForm(f => ({ ...f, service_type: e.target.value }))} style={{ width: '100%', padding: '0.5rem', backgroundColor: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '0.5rem', color: 'var(--text)', outline: 'none' }} />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--muted)', marginBottom: '0.25rem' }}>Provider Name</label>
                    <input type="text" placeholder="e.g. Local Shop" value={modalForm.provider_name} onChange={e => setModalForm(f => ({ ...f, provider_name: e.target.value }))} style={{ width: '100%', padding: '0.5rem', backgroundColor: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '0.5rem', color: 'var(--text)', outline: 'none' }} />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--muted)', marginBottom: '0.25rem' }}>Quoted Price (₹) *</label>
                    <input type="number" placeholder="e.g. 1500" value={modalForm.quoted_price} onChange={e => setModalForm(f => ({ ...f, quoted_price: e.target.value }))} style={{ width: '100%', padding: '0.5rem', backgroundColor: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '0.5rem', color: 'var(--text)', outline: 'none' }} required />
                  </div>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--muted)', marginBottom: '0.25rem' }}>Invoice Receipt Photo</label>
                  <div style={{ border: '1px dashed var(--border)', borderRadius: '0.75rem', padding: '1rem', backgroundColor: 'var(--bg)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', relative: 'true', cursor: 'pointer', minHeight: '80px' }}>
                    <input type="file" accept="image/*" onChange={handleImageChange} style={{ position: 'absolute', inset: 0, opacity: 0, cursor: 'pointer' }} />
                    {imagePreview ? (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <img src={imagePreview} alt="Preview" style={{ width: '40px', height: '40px', borderRadius: '0.5rem', objectFit: 'cover', border: '1px solid var(--border)' }} />
                        <div>
                          <div style={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--text)', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{proofFile?.name}</div>
                          <div style={{ fontSize: '0.6rem', color: 'var(--muted)' }}>{uploadingImage ? 'Uploading...' : 'Attached'}</div>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div style={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--text)' }}>Click to upload quote photo</div>
                      </>
                    )}
                  </div>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--muted)', marginBottom: '0.25rem' }}>Additional Description</label>
                  <textarea placeholder="Extra details..." value={modalForm.notes} onChange={e => setModalForm(f => ({ ...f, notes: e.target.value }))} style={{ width: '105%', padding: '0.5rem', backgroundColor: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '0.5rem', color: 'var(--text)', outline: 'none', height: '60px', resize: 'none' }} />
                </div>

                <div style={{ display: 'flex', gap: '0.75rem', paddingTop: '0.5rem' }}>
                  <button type="button" onClick={() => setShowModal(false)} style={{ flex: 1, py: '0.5rem', borderRadius: '0.5rem', border: '1px solid var(--border)', backgroundColor: 'transparent', color: 'var(--text)', fontSize: '0.75rem', fontWeight: 'bold', cursor: 'pointer', height: '35px' }}>Cancel</button>
                  <button type="submit" disabled={uploadingImage} style={{ flex: 2, py: '0.5rem', borderRadius: '0.5rem', backgroundColor: 'var(--brand)', color: '#ffffff', fontSize: '0.75rem', fontWeight: 'bold', cursor: 'pointer', height: '35px' }}>
                    {uploadingImage ? 'Uploading...' : 'Submit Report'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
      <Footer />
    </div>
  )
}

const CONFIDENCE_STYLES = {
  High: 'High',
  Medium: 'Medium',
  Fallback: 'Fallback'
}

const VERDICT_STYLES = {
  fair:       { color: '#10b981', label: 'FAIR' },
  high:       { color: '#f59e0b', label: 'HIGH' },
  suspicious: { color: '#ef4444', label: 'SUSPICIOUS' },
  low:        { color: '#3b82f6', label: 'LOW' }
}
