import Link from 'next/link'
import ThemeToggle from './ThemeToggle'

// The lab is served at arach.dev/lab, so the header mirrors arach.dev's.
// Site links are plain anchors: next/link would prefix them with the /lab basePath.
const SITE_NAV = [
  { href: '/ideas', label: 'Notes' },
  { href: '/github', label: 'GitHub' },
  { href: '/about', label: 'About' },
]

const LAB_NAV = [
  { key: 'home', label: 'Overview', href: '/' },
  { key: 'bench', label: 'Bench', href: '/#bench' },
  { key: 'next', label: 'Next', href: '/#next' },
  { key: 'ideas', label: 'Ideas', href: '/ideas' },
]

export default function SiteHeader({ current = 'home' }) {
  return (
    <>
      <header className="site-header">
        <div className="site-header-inner">
          <a href="/" className="site-wordmark">
            arach<span>.dev</span>
          </a>
          <nav className="site-nav" aria-label="Site">
            <ul>
              <li>
                <Link href="/" aria-current="page">[ Lab ]</Link>
              </li>
              {SITE_NAV.map((item) => (
                <li key={item.href}>
                  <a href={item.href}>{item.label}</a>
                </li>
              ))}
              <li className="hide-sm">
                <a href="https://arach.io">Writing ↗</a>
              </li>
            </ul>
            <ThemeToggle />
          </nav>
        </div>
      </header>
      <nav className="lab-subnav" aria-label="Training lab">
        <div className="lab-shell lab-subnav-inner">
          <span className="lab-fig lab-subnav-title">Training lab</span>
          <ul className="lab-fig">
            {LAB_NAV.map((item) => (
              <li key={item.key}>
                <Link
                  href={item.href}
                  aria-current={current === item.key ? 'page' : undefined}
                >
                  {current === item.key ? `[ ${item.label} ]` : item.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </nav>
    </>
  )
}
