import StatGrid from './StatGrid'

function formatSlice(slice) {
  if (slice === 'title') return 'Title'
  if (slice === 'intent') return 'Intent'
  if (slice === 'restraint') return 'Restraint'
  return slice
}

export default function TitleIntentPackPanel({ summary, cards, compact = false, detailOnly = false }) {
  const statItems = [
    { label: 'Cards', value: String(summary.cards) },
    { label: 'Intent Labels', value: String(summary.intents.length) },
    { label: 'Restraint Cases', value: String(summary.restraintCards) },
  ]

  if (detailOnly) {
    return (
      <section className="data-band semantic-band semantic-band-detail">
        <div className="data-band-header">
          <div>
            <p className="section-kicker">Draft Cards</p>
            <h2>The first 12 cases</h2>
            <p>
              The current pack is small on purpose: enough range to expose title quality,
              action extraction, and restraint failures without turning into a giant benchmark.
            </p>
          </div>
          <span className="tiny-chip">
            {summary.titleCards}/{summary.intentCards}/{summary.restraintCards}
          </span>
        </div>

        <div className="semantic-models-card semantic-models-card-detail">
          <div className="table-wrap semantic-table-wrap">
            <table className="scores-table semantic-scores-table">
              <thead>
                <tr>
                  <th>Card</th>
                  <th>Slice</th>
                  <th>Why It Exists</th>
                </tr>
              </thead>
              <tbody>
                {cards.map((card) => (
                  <tr key={card.id}>
                    <td className="col-identifier">{card.id}</td>
                    <td>
                      <span className="category-chip">{formatSlice(card.packSlice)}</span>
                    </td>
                    <td>{card.whyItMatters}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section className={`data-band semantic-band${compact ? ' semantic-band-compact' : ''}`}>
      <div className="data-band-header">
        <div>
          <p className="section-kicker">Current Pack</p>
          <h2>Auto-title plus tiny intent extraction.</h2>
          <p>
            {compact
              ? 'A short benchmark for title quality, tiny intent labels, and restraint.'
              : 'The clean-slate benchmark asks one narrow question: can a short voice note become more usable with a good title and only the clearest action label?'}
          </p>
        </div>
        <span className="tiny-chip">title_intent_v1</span>
      </div>

      <div className="data-band-body">
        <StatGrid items={statItems} />
      </div>

      <div className="semantic-principles">
        {summary.weights.map((item) => (
          <div key={item.label} className="semantic-principle-card">
            <span className="stat-label">{item.label}</span>
            <span className="stat-value">{item.value}</span>
            <p>{item.note}</p>
          </div>
        ))}
      </div>

      <div className="semantic-card-row">
        <div className="semantic-card-list">
          <span className="stat-label">Intent Set</span>
          <ul>
            {summary.intents.map((intent) => (
              <li key={intent}>{intent}</li>
            ))}
          </ul>
        </div>

        <div className="semantic-card-list">
          <span className="stat-label">Design Rules</span>
          <ul>
            {summary.principles.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>

      {!compact ? (
        <div className="semantic-models-card">
          <div className="semantic-models-header">
            <div>
              <p className="section-kicker">Draft Cards</p>
              <h4>The first 12 cases</h4>
            </div>
            <span className="tiny-chip">
              {summary.titleCards}/{summary.intentCards}/{summary.restraintCards}
            </span>
          </div>

          <div className="table-wrap semantic-table-wrap">
            <table className="scores-table semantic-scores-table">
              <thead>
                <tr>
                  <th>Card</th>
                  <th>Slice</th>
                  <th>Why It Exists</th>
                </tr>
              </thead>
              <tbody>
                {cards.map((card) => (
                  <tr key={card.id}>
                    <td className="col-identifier">{card.id}</td>
                    <td>
                      <span className="category-chip">{formatSlice(card.packSlice)}</span>
                    </td>
                    <td>{card.whyItMatters}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </section>
  )
}
