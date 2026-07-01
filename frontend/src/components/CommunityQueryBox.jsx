'use client'

import { useState, useRef, useEffect } from 'react'

const SUGGESTIONS = [
  "What is the average AC gas refill price?",
  "Are motor repairs in Bangalore expensive?",
  "Show me TV panel replacement rates.",
  "What's the typical geyser heating element cost?"
]

export default function CommunityQueryBox({ currentCity, currentAppliance }) {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      sender: 'ai',
      text: `Hello! I am your Service-One Community Concierge. Ask me anything about repair rates for ${currentAppliance || 'appliances'} in ${currentCity || 'your city'}.`
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const chatEndRef = useRef(null)

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000'

  // Scroll to bottom on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleAsk = async (queryText) => {
    if (!queryText.trim() || loading) return

    // 1. Add User Message
    const userMsg = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: queryText
    }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    // 2. Call RAG API
    try {
      const res = await fetch(`${apiBase}/api/community-query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: queryText,
          city: currentCity,
          appliance: currentAppliance
        })
      })
      if (!res.ok) throw new Error("API error")
      const data = await res.json()

      // 3. Add AI Message
      const aiMsg = {
        id: `ai-${Date.now()}`,
        sender: 'ai',
        text: data.answer,
        dataPoints: data.data_points_used,
        reports: data.reports || []
      }
      setMessages(prev => [...prev, aiMsg])
    } catch (err) {
      console.error(err)
      const errorMsg = {
        id: `error-${Date.now()}`,
        sender: 'ai',
        text: "Sorry, I am currently unable to retrieve community metrics. Please verify the backend is running."
      }
      setMessages(prev => [...prev, errorMsg])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      background: '#ffffff',
      border: '1px solid #e2e8f0',
      borderRadius: '16px',
      boxShadow: '0 4px 20px -2px rgba(148, 163, 184, 0.08)',
      display: 'flex',
      flexDirection: 'column',
      height: '420px',
      overflow: 'hidden',
      marginTop: '1.5rem',
      marginBottom: '1.5rem'
    }}>
      {/* Chat Header */}
      <div style={{
        background: 'linear-gradient(135deg, #1c446b 0%, #173757 100%)',
        padding: '14px 20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        color: '#ffffff'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: '#10b981',
            boxShadow: '0 0 0 3px rgba(16, 185, 129, 0.3)'
          }} />
          <div>
            <h4 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 700 }}>Ask AI Community Concierge</h4>
            <span style={{ fontSize: '0.7rem', opacity: 0.8 }}>RAG pricing lookup layer</span>
          </div>
        </div>
      </div>

      {/* Messages Feed */}
      <div style={{
        flex: 1,
        padding: '20px',
        overflowY: 'auto',
        background: '#f8fafc',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px'
      }}>
        {messages.map((m) => {
          const isAI = m.sender === 'ai'
          return (
            <div key={m.id} style={{
              display: 'flex',
              justifyContent: isAI ? 'flex-start' : 'flex-end',
              width: '100%'
            }}>
              <div style={{
                maxWidth: '85%',
                background: isAI ? '#ffffff' : '#1c446b',
                color: isAI ? '#334155' : '#ffffff',
                border: '1px solid',
                borderColor: isAI ? '#e2e8f0' : '#1c446b',
                borderRadius: isAI ? '12px 12px 12px 2px' : '12px 12px 2px 12px',
                padding: '10px 14px',
                fontSize: '0.85rem',
                lineHeight: '1.45',
                boxShadow: isAI ? '0 2px 8px -2px rgba(148, 163, 184, 0.05)' : 'none'
              }}>
                <div>{m.text}</div>
                {isAI && m.reports && m.reports.length > 0 && (
                  <div style={{
                    marginTop: '10px',
                    borderTop: '1px solid #e2e8f0',
                    paddingTop: '8px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px'
                  }}>
                    <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      Retrieved Community Records:
                    </span>
                    {m.reports.map((rep, rIdx) => (
                      <div key={rIdx} style={{
                        background: '#f8fafc',
                        border: '1px solid #e2e8f0',
                        borderRadius: '6px',
                        padding: '6px 8px',
                        fontSize: '0.75rem',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}>
                        <span style={{ fontWeight: 600, color: '#1c446b' }}>
                          {rep.service_type}
                        </span>
                        <span style={{ 
                          color: rep.verdict === 'fair' ? '#10b981' : rep.verdict === 'high' ? '#f59e0b' : '#ef4444', 
                          fontWeight: 700 
                        }}>
                          ₹{rep.quoted_price} ({rep.verdict})
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                {isAI && m.dataPoints !== undefined && (
                  <div style={{
                    fontSize: '0.68rem',
                    color: '#94a3b8',
                    marginTop: '6px',
                    borderTop: '1px solid #f1f5f9',
                    paddingTop: '4px'
                  }}>
                    Source: {m.dataPoints} crowdsourced invoices
                  </div>
                )}
              </div>
            </div>
          )
        })}

        {/* Loading Indicator */}
        {loading && (
          <div style={{ display: 'flex', justifyContent: 'flex-start', width: '100%' }}>
            <div style={{
              background: '#ffffff',
              border: '1px solid #e2e8f0',
              borderRadius: '12px 12px 12px 2px',
              padding: '12px 16px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}>
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#94a3b8', animation: 'bounce 1.4s infinite ease-in-out' }} />
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#94a3b8', animation: 'bounce 1.4s infinite ease-in-out 0.2s' }} />
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#94a3b8', animation: 'bounce 1.4s infinite ease-in-out 0.4s' }} />
              <style>{`
                @keyframes bounce {
                  0%, 80%, 100% { transform: scale(0); }
                  40% { transform: scale(1.0); }
                }
              `}</style>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Suggested Quick Chips */}
      <div style={{
        background: '#f8fafc',
        padding: '8px 16px',
        borderTop: '1px solid #e2e8f0',
        display: 'flex',
        gap: '8px',
        overflowX: 'auto',
        whiteSpace: 'nowrap'
      }}>
        {SUGGESTIONS.map((s, idx) => (
          <button
            key={idx}
            onClick={() => handleAsk(s)}
            style={{
              background: '#ffffff',
              border: '1px solid #cbd5e1',
              borderRadius: '999px',
              padding: '6px 12px',
              fontSize: '0.75rem',
              color: '#1c446b',
              fontWeight: 600,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'all 0.2s ease'
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.borderColor = '#1c446b'
              e.currentTarget.style.background = '#f1f5f9'
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.borderColor = '#cbd5e1'
              e.currentTarget.style.background = '#ffffff'
            }}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Message Input Box */}
      <form
        onSubmit={(e) => {
          e.preventDefault()
          handleAsk(input)
        }}
        style={{
          display: 'flex',
          borderTop: '1px solid #e2e8f0',
          padding: '10px 16px',
          background: '#ffffff'
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={`Ask about ${currentAppliance || 'appliance'} repair costs...`}
          disabled={loading}
          style={{
            flex: 1,
            border: 'none',
            outline: 'none',
            fontSize: '0.85rem',
            color: '#334155'
          }}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          style={{
            background: 'none',
            border: 'none',
            color: input.trim() ? '#1c446b' : '#94a3b8',
            cursor: input.trim() ? 'pointer' : 'default',
            fontWeight: 700,
            fontSize: '0.85rem',
            padding: '4px 8px'
          }}
        >
          Send
        </button>
      </form>
    </div>
  )
}
