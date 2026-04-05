export default function BenchmarkSnapshot({ summary, v1Rows }) {
  const metrics = [
    { label: 'Pass Rate', value: `${Math.round(summary.pass_rate * 100)}%`, note: 'Strong models should look clearly strong here.' },
    { label: 'Task Score', value: summary.task_score.toFixed(2), note: 'Did the model actually do the job?' },
    { label: 'Usable', value: summary.usable_score.toFixed(2), note: 'Could the product use this with light normalization?' },
    { label: 'Contract', value: summary.contract_score.toFixed(2), note: 'How closely did it follow the preferred exact schema?' },
  ]

  return (
    <section className="data-band">
      <div className="data-band-header">
        <div>
          <p className="section-kicker">Calibration Snapshot</p>
          <h3>What the benchmark is saying right now.</h3>
          <p>
            `gpt-4.1` is the first healthy anchor on the new benchmark, while the original
            24-card pack still works as a broader stress test for open and local-ish models.
          </p>
        </div>
        <span className="tiny-chip">{summary.provider}</span>
      </div>
      <div className="data-band-body">
        <div className="metric-row">
          {metrics.map((metric) => (
            <div key={metric.label} className="metric-card">
              <span className="stat-label">{metric.label}</span>
              <span className="stat-value">{metric.value}</span>
              <div className="metric-note">{metric.note}</div>
            </div>
          ))}
        </div>
        <div style={{ height: '1rem' }} />
        <div className="table-wrap">
          <table className="scores-table">
            <thead>
              <tr>
                <th>Model</th>
                <th>Pack</th>
                <th>Pass</th>
                <th>Avg</th>
                <th>Signal</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="col-identifier">{summary.model}</td>
                <td><span className="pack-chip">core_eval_v2</span></td>
                <td className="col-score">{summary.passed}/{summary.cards}</td>
                <td className="col-score">{summary.average_score.toFixed(2)}</td>
                <td>{summary.signal || 'Healthy top-end anchor'}</td>
              </tr>
              {v1Rows.map((row) => (
                <tr key={row.model}>
                  <td className="col-identifier">{row.model}</td>
                  <td><span className="pack-chip">local_intelligence v1</span></td>
                  <td className="col-score">{row.pass}</td>
                  <td className="col-score">{row.avg}</td>
                  <td>{row.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
