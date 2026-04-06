const siteUrl = 'https://www.arach.dev'
const labBasePath = '/lab'

export function absoluteUrl(pathname = '/') {
  return new URL(pathname, siteUrl).toString()
}

export function labUrl(pathname = '') {
  if (!pathname) return labBasePath
  const normalized = pathname.startsWith('/') ? pathname : `/${pathname}`
  return `${labBasePath}${normalized}`
}

export function createLabMetadata({
  title,
  description,
  pathname = '',
  imagePath = '/og/lab/index.png',
  type = 'website',
}) {
  const url = absoluteUrl(labUrl(pathname))
  const image = absoluteUrl(labUrl(imagePath))

  return {
    title,
    description,
    metadataBase: new URL(siteUrl),
    alternates: {
      canonical: url,
    },
    openGraph: {
      title,
      description,
      type,
      url,
      images: [
        {
          url: image,
          width: 1200,
          height: 630,
          alt: title,
        },
      ],
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
      images: [image],
    },
  }
}
