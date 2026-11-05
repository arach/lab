import { Geist, Geist_Mono } from 'next/font/google'
import Script from 'next/script'
import { createLabMetadata } from '../lib/site-metadata'
import './globals.css'
import './lab.css'

const sans = Geist({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
})

const mono = Geist_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
})

export const metadata = createLabMetadata({
  title: 'Training Lab',
  description: 'Ideas, experiments, benchmark notes, and daily TILs from Training Lab.',
  pathname: '',
  imagePath: '/og/lab/index.png',
})

// Same boot script as arach.dev, so /lab opens in the theme chosen there.
const themeBootScript = `(function(){var t;try{t=localStorage.getItem('site-theme')}catch(e){}if(t!=='default'&&t!=='dark'){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'default'}document.documentElement.setAttribute('data-theme',t)})();`

export default function RootLayout({ children }) {
  return (
    <html
      lang="en"
      className={`${sans.variable} ${mono.variable}`}
      data-theme="default"
      suppressHydrationWarning
    >
      <head>
        <Script id="theme-boot" strategy="beforeInteractive">{themeBootScript}</Script>
      </head>
      <body className={sans.className}>{children}</body>
    </html>
  )
}
