/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    const api = process.env.NEXT_PUBLIC_API_URL || 'http://app:8000'
    return [
      { source: '/api/:path*', destination: `${api}/:path*` },
      { source: '/models/:path*', destination: `${api}/models/:path*` },
      { source: '/quiz/:path*', destination: `${api}/quiz/:path*` },
      { source: '/lesson-plan/:path*', destination: `${api}/lesson-plan/:path*` },
      { source: '/chat', destination: `${api}/chat` },
      { source: '/graph/:path*', destination: `${api}/graph/:path*` },
      { source: '/progress/:path*', destination: `${api}/progress/:path*` },
      { source: '/gamification/:path*', destination: `${api}/gamification/:path*` },
      { source: '/activity/:path*', destination: `${api}/activity/:path*` },
      { source: '/diagram/:path*', destination: `${api}/diagram/:path*` },
      { source: '/recovery/:path*', destination: `${api}/recovery/:path*` },
    ]
  },
}

module.exports = nextConfig
