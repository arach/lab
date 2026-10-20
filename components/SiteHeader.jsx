import Link from 'next/link'

const NAV = [
  { key: 'bench', label: 'Bench', href: '/#bench' },
  { key: 'next', label: 'Next', href: '/#next' },
  { key: 'ideas', label: 'Ideas', href: '/ideas' },
]

export default function SiteHeader({ current }) {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <Link href="/" className="brand lab-brand">
          <span className="lab-brand-dot" aria-hidden="true" />
          Training Lab
        </Link>
        <nav className="lab-nav" aria-label="Primary">
          {NAV.map((item) => (
            <Link
              key={item.key}
              href={item.href}
              className={`nav-link${current === item.key ? ' is-current' : ''}`}
              aria-current={current === item.key ? 'page' : undefined}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  )
}
