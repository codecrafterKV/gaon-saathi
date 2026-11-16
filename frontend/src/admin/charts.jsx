import { useState } from 'react'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { BarChart3, Table2 } from 'lucide-react'
import { dayLabel, formatNumber, monthLabel } from '../lib/format'

// Single-series charts: one hue each, recessive grid, text in text tokens.
const INK = { primary: '#0b1f3a', secondary: '#475569', muted: '#94a3b8', grid: '#e2e8f0' }
export const HUES = { green: '#0b8f4a', navy: '#2b4f7d', teal: '#0e7490' }

const SHORT_CATEGORY = {
  public_space_encroachment: 'Encroachment',
  illegal_tree_cutting: 'Tree cutting',
  development_fund_misuse: 'Fund misuse',
  road_drainage: 'Roads & drainage',
  ration_distribution: 'Ration',
  public_resource_misuse: 'Resource misuse',
  corruption_governance: 'Corruption / governance',
  other: 'Other',
}
const SHORT_STATUS = {
  received: 'Received', under_review: 'Under review', evidence_verification: 'Evidence check',
  action_in_progress: 'In progress', forwarded: 'Forwarded', resolved: 'Resolved', rejected: 'Rejected', closed: 'Closed',
}

export function ChartCard({ title, description, children, table, empty, action }) {
  const [showTable, setShowTable] = useState(false)
  return (
    <section className="card flex flex-col p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-bold">{title}</h2>
          {description && <p className="mt-0.5 text-xs text-slate-500">{description}</p>}
        </div>
        <div className="flex items-center gap-1">
          {action}
          {!empty && (
            <button type="button" onClick={() => setShowTable((v) => !v)}
              className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-slate-500 hover:bg-slate-100 hover:text-navy-900"
              aria-pressed={showTable}>
              {showTable ? <><BarChart3 className="h-3.5 w-3.5" /> Chart</> : <><Table2 className="h-3.5 w-3.5" /> Table</>}
            </button>
          )}
        </div>
      </div>
      <div className="mt-4 flex-1">
        {empty ? (
          <div className="flex h-56 flex-col items-center justify-center rounded-xl bg-slate-50 text-center text-sm text-slate-500">
            <BarChart3 className="mb-2 h-6 w-6 text-slate-300" aria-hidden="true" />
            No complaints to show yet.
          </div>
        ) : showTable ? table : children}
      </div>
    </section>
  )
}

function DataTable({ head, rows }) {
  return (
    <div className="max-h-72 overflow-auto rounded-xl border border-slate-200">
      <table className="table-base">
        <thead><tr>{head.map((h, i) => <th key={h} className={i === head.length - 1 ? '!text-right' : ''}>{h}</th>)}</tr></thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((r) => (
            <tr key={r.join('|')}>{r.map((c, i) => <td key={i} className={i === r.length - 1 ? 'text-right font-semibold tabular-nums text-navy-900' : ''}>{c}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function TooltipBox({ active, payload, labelKey = 'full', unit = 'complaints' }) {
  if (!active || !payload?.length) return null
  const item = payload[0].payload
  return (
    <div className="rounded-lg bg-navy-950 px-3 py-2 text-xs text-white shadow-lift">
      <p className="font-semibold">{item[labelKey]}</p>
      <p className="mt-0.5 text-navy-200"><span className="font-bold text-white tabular-nums">{formatNumber(payload[0].value)}</span> {unit}</p>
    </div>
  )
}

function HorizontalBars({ data, color, height }) {
  const max = Math.max(...data.map((d) => d.count), 1)
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 0, right: 36, bottom: 0, left: 0 }} barCategoryGap={6}>
        <CartesianGrid horizontal={false} stroke={INK.grid} strokeDasharray="0" />
        <XAxis type="number" allowDecimals={false} domain={[0, Math.ceil(max * 1.1)]} tick={{ fill: INK.muted, fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis type="category" dataKey="short" width={142} tick={{ fill: INK.secondary, fontSize: 12 }} axisLine={false} tickLine={false} />
        <Tooltip cursor={{ fill: 'rgba(11,31,58,0.04)' }} content={<TooltipBox />} />
        <Bar dataKey="count" fill={color} radius={[0, 4, 4, 0]} maxBarSize={22} minPointSize={2} animationDuration={600}>
          <LabelList dataKey="count" position="right" fill={INK.primary} fontSize={12} fontWeight={600} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

export function CategoryChart({ data }) {
  const rows = data.map((d) => ({ ...d, short: SHORT_CATEGORY[d.category], full: d.label }))
  return (
    <ChartCard title="Complaints by category" description="All complaints in the selected data set"
      empty={rows.every((r) => r.count === 0)}
      table={<DataTable head={['Category', 'Complaints']} rows={rows.map((r) => [r.label, formatNumber(r.count)])} />}>
      <HorizontalBars data={rows} color={HUES.green} height={300} />
    </ChartCard>
  )
}

export function StatusChart({ data }) {
  const rows = data.map((d) => ({ ...d, short: SHORT_STATUS[d.status], full: d.label }))
  return (
    <ChartCard title="Complaints by status" description="Current status of each complaint"
      empty={rows.every((r) => r.count === 0)}
      table={<DataTable head={['Status', 'Complaints']} rows={rows.map((r) => [r.label, formatNumber(r.count)])} />}>
      <HorizontalBars data={rows} color={HUES.navy} height={300} />
    </ChartCard>
  )
}

export function VillageChart({ data, distinct }) {
  const rows = data.map((d) => ({ ...d, short: d.village.length > 20 ? `${d.village.slice(0, 19)}...` : d.village, full: `${d.village}, ${d.district} (${d.state})` }))
  return (
    <ChartCard title="Village-wise distribution" description={`Top ${rows.length} of ${distinct} village${distinct === 1 ? '' : 's'}`}
      empty={rows.length === 0}
      table={<DataTable head={['Village', 'District', 'State', 'Complaints']} rows={rows.map((r) => [r.village, r.district, r.state, formatNumber(r.count)])} />}>
      <HorizontalBars data={rows} color={HUES.teal} height={Math.max(160, rows.length * 30 + 20)} />
    </ChartCard>
  )
}

export function TimelineChart({ daily, monthly }) {
  const [range, setRange] = useState('monthly')
  const rows = range === 'monthly'
    ? monthly.map((m) => ({ key: m.month, short: monthLabel(m.month), full: monthLabel(m.month), count: m.count }))
    : daily.map((d) => ({ key: d.date, short: dayLabel(d.date), full: dayLabel(d.date), count: d.count }))
  const total = rows.reduce((s, r) => s + r.count, 0)
  const toggle = (
    <div className="inline-flex rounded-lg bg-slate-100 p-0.5" role="radiogroup" aria-label="Time range">
      {[['daily', '30 days'], ['monthly', '12 months']].map(([v, label]) => (
        <button key={v} type="button" role="radio" aria-checked={range === v} onClick={() => setRange(v)}
          className={`rounded-md px-2 py-1 text-xs font-medium ${range === v ? 'bg-white text-navy-900 shadow-sm' : 'text-slate-500'}`}>{label}</button>
      ))}
    </div>
  )
  return (
    <ChartCard title="Complaints received over time" description={`${formatNumber(total)} in the last ${range === 'monthly' ? '12 months' : '30 days'}`}
      action={toggle} empty={total === 0}
      table={<DataTable head={[range === 'monthly' ? 'Month' : 'Day', 'Complaints']} rows={[...rows].reverse().map((r) => [r.full, formatNumber(r.count)])} />}>
      <ResponsiveContainer width="100%" height={260}>
        <AreaChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
          <defs>
            <linearGradient id="gs-area" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={HUES.green} stopOpacity={0.22} />
              <stop offset="100%" stopColor={HUES.green} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid vertical={false} stroke={INK.grid} />
          <XAxis dataKey="short" tick={{ fill: INK.muted, fontSize: 11 }} axisLine={false} tickLine={false} interval="preserveStartEnd" minTickGap={18} />
          <YAxis allowDecimals={false} tick={{ fill: INK.muted, fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip content={<TooltipBox />} cursor={{ stroke: INK.secondary, strokeWidth: 1, strokeDasharray: '3 3' }} />
          <Area type="monotone" dataKey="count" stroke={HUES.green} strokeWidth={2} fill="url(#gs-area)" animationDuration={600}
            activeDot={{ r: 5, fill: HUES.green, stroke: '#fff', strokeWidth: 2 }} dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}
