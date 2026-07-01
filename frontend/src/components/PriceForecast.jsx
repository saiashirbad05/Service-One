'use client'

import React from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from 'recharts'

export default function PriceForecast({ trendData, forecastText, appliance, city, loading }) {
  if (loading) {
    return (
      <div className="result-card glass-panel" style={{ padding: '24px', minHeight: '260px' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#1e293b', marginBottom: '16px' }}>
          Analyzing Pricing Forecast...
        </h3>
        <div style={{ height: '140px', background: '#f1f5f9', borderRadius: '8px', animation: 'pulse 1.5s infinite', marginBottom: '16px' }} />
        <div style={{ height: '40px', background: '#e2e8f0', borderRadius: '6px', animation: 'pulse 1.5s infinite' }} />
      </div>
    )
  }

  // Format month to standard Indian format (e.g. 2026-01 to Jan)
  const formatMonth = (monthStr) => {
    if (!monthStr) return ''
    const [year, month] = monthStr.split('-')
    const date = new Date(parseInt(year), parseInt(month) - 1)
    return date.toLocaleString('en-IN', { month: 'short' })
  }

  const hasEnoughData = trendData && trendData.length >= 3

  return (
    <div className="result-card glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#1e293b', margin: 0 }}>
          Price Trend — {appliance?.toUpperCase()} in {city}
        </h3>
        <p style={{ fontSize: '0.8rem', color: '#64748b', margin: '4px 0 0 0' }}>
          Historical average prices calculated from community reports over the last 6 months.
        </p>
      </div>

      {!hasEnoughData ? (
        <div style={{
          height: '200px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#f8fafc',
          borderRadius: '12px',
          border: '1px dashed #cbd5e1',
          color: '#64748b',
          fontSize: '0.9rem',
          textAlign: 'center',
          padding: '20px',
          lineHeight: '1.6'
        }}>
          Not enough community data yet for this appliance in this city.<br />
          Submit more invoices to unlock regional forecasting model.
        </div>
      ) : (
        <>
          <div style={{ width: '100%', height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.2} vertical={false} />
                <XAxis 
                  dataKey="month" 
                  tickFormatter={formatMonth} 
                  tick={{ fill: '#64748b', fontSize: 11 }}
                  stroke="#cbd5e1"
                />
                <YAxis 
                  tickFormatter={(val) => `₹${val}`}
                  tick={{ fill: '#64748b', fontSize: 11 }}
                  stroke="#cbd5e1"
                />
                <Tooltip 
                  formatter={(value, name) => {
                    if (name === 'avg_price') return [`₹${value}`, 'Average Price']
                    return [value, 'Reports Count']
                  }}
                  labelFormatter={(label) => `Month: ${formatMonth(label)}`}
                  contentStyle={{ background: 'rgba(255, 255, 255, 0.95)', border: '1px solid #cbd5e1', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}
                />
                <Line 
                  type="monotone" 
                  dataKey="avg_price" 
                  stroke="#7c3aed" 
                  strokeWidth={2.5} 
                  activeDot={{ r: 6 }} 
                  dot={{ stroke: '#7c3aed', strokeWidth: 2, r: 4, fill: '#fff' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {forecastText && (
            <div style={{
              background: '#f5f3ff',
              borderLeft: '4px solid #7c3aed',
              padding: '12px 16px',
              borderRadius: '0 8px 8px 0',
              marginTop: '4px'
            }}>
              <span style={{ display: 'block', fontSize: '0.75rem', fontWeight: 850, textTransform: 'uppercase', color: '#7c3aed', letterSpacing: '0.05em', marginBottom: '4px' }}>
                AI Forecast Analysis
              </span>
              <p style={{ margin: 0, fontSize: '0.85rem', color: '#4c1d95', lineHeight: '1.5' }}>
                {forecastText}
              </p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
