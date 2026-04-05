export default function StatGrid({ items = [] }) {
  return (
    <div className="stat-grid">
      {items.map((item) => (
        <div key={item.label} className="stat-card">
          <span className="stat-label">{item.label}</span>
          <span className="stat-value">{item.value}</span>
        </div>
      ))}
    </div>
  )
}
