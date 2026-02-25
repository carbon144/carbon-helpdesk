import React from 'react'

export function SkeletonLine({ width = '100%', height = '14px', className = '' }) {
  return <div className={`skeleton ${className}`} style={{ width, height }} />
}

export function SkeletonCircle({ size = '32px', className = '' }) {
  return <div className={`skeleton ${className}`} style={{ width: size, height: size, borderRadius: '50%' }} />
}

export function SkeletonCard({ className = '' }) {
  return (
    <div className={`rounded-xl p-4 border ${className}`} style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}>
      <div className="flex items-center justify-between mb-3">
        <SkeletonLine width="60%" height="10px" />
        <SkeletonCircle size="32px" />
      </div>
      <SkeletonLine width="40%" height="28px" />
    </div>
  )
}

export function SkeletonTicketRow() {
  return (
    <div className="flex items-center gap-4 px-6 py-4 border-b" style={{ borderColor: 'var(--border-color)' }}>
      <SkeletonCircle size="16px" />
      <SkeletonLine width="50px" height="12px" />
      <div className="flex-1 space-y-1.5">
        <SkeletonLine width="60%" height="13px" />
        <SkeletonLine width="40%" height="10px" />
      </div>
      <SkeletonLine width="70px" height="22px" />
      <SkeletonLine width="50px" height="22px" />
      <SkeletonLine width="60px" height="12px" />
      <SkeletonLine width="80px" height="12px" />
    </div>
  )
}

export function SkeletonTicketList({ rows = 8 }) {
  return (
    <div>
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonTicketRow key={i} />
      ))}
    </div>
  )
}

export function SkeletonDashboard() {
  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-5">
        <SkeletonLine width="160px" height="28px" />
        <SkeletonLine width="120px" height="36px" />
      </div>
      <div className="flex gap-2 mb-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonLine key={i} width="120px" height="36px" />
        ))}
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl p-4 border" style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}>
          <SkeletonLine width="140px" height="14px" className="mb-4" />
          <SkeletonLine width="100%" height="200px" />
        </div>
        <div className="rounded-xl p-4 border" style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}>
          <SkeletonLine width="140px" height="14px" className="mb-4" />
          <SkeletonLine width="100%" height="200px" />
        </div>
      </div>
    </div>
  )
}
