'use client'

// Shares arach.dev's saved theme: same localStorage key, same data-theme values.
const STORAGE_KEY = 'site-theme'

function toggle() {
  const root = document.documentElement
  const next = root.getAttribute('data-theme') === 'dark' ? 'default' : 'dark'
  root.setAttribute('data-theme', next)
  try {
    localStorage.setItem(STORAGE_KEY, next)
  } catch {}
}

export default function ThemeToggle() {
  return (
    <button type="button" className="theme-toggle" onClick={toggle} aria-label="Toggle light and dark theme">
      <svg className="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
      </svg>
      <svg className="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
      </svg>
    </button>
  )
}
