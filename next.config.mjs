const basePath = process.env.BASE_PATH || ''
const isStaticExport = process.env.STATIC_EXPORT === '1'

/** @type {import('next').NextConfig} */
const nextConfig = {
  basePath,
  assetPrefix: basePath || undefined,
  images: {
    unoptimized: true,
  },
}

if (isStaticExport) {
  nextConfig.output = 'export'
  nextConfig.trailingSlash = true
}

export default nextConfig
