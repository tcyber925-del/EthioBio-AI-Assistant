/** @type {import('next').NextConfig} */
const createNextIntlPlugin = require('next-intl/plugin');
const withNextIntl = createNextIntlPlugin('./i18n.ts');

const nextConfig = {
  async rewrites() {
    const api = process.env.NEXT_PUBLIC_API_URL || 'http://app:8000'
    return [
      { source: '/api/v1/:path*', destination: `${api}/api/v1/:path*` },
      { source: '/api/:path*', destination: `${api}/:path*` },
      { source: '/api/lesson-plan', destination: `${api}/lesson-plan` },
      { source: '/api/lesson-plan/:path*', destination: `${api}/lesson-plan/:path*` },
      { source: '/api/quiz', destination: `${api}/quiz` },
      { source: '/api/quiz/:path*', destination: `${api}/quiz/:path*` },
      { source: '/api/interventions', destination: `${api}/interventions` },
      { source: '/api/interventions/:path*', destination: `${api}/interventions/:path*` },
      { source: '/models', destination: `${api}/models` },
      { source: '/models/:path*', destination: `${api}/models/:path*` },
      { source: '/quiz', destination: `${api}/quiz` },
      { source: '/quiz/:path*', destination: `${api}/quiz/:path*` },
      { source: '/lesson-plan', destination: `${api}/lesson-plan` },
      { source: '/lesson-plan/:path*', destination: `${api}/lesson-plan/:path*` },
      { source: '/chat', destination: `${api}/chat` },
      { source: '/graph/:path*', destination: `${api}/graph/:path*` },
      { source: '/progress/:path*', destination: `${api}/progress/:path*` },
      { source: '/diagram', destination: `${api}/diagram` },
      { source: '/diagram/:path*', destination: `${api}/diagram/:path*` },
      { source: '/diagrams/static/:path*', destination: `${api}/diagrams/static/:path*` },
      { source: '/intelligence/:path*', destination: `${api}/intelligence/:path*` },
      { source: '/auth/:path*', destination: `${api}/auth/:path*` },
      { source: '/teacher/:path*', destination: `${api}/teacher/:path*` },
      { source: '/recovery/:path*', destination: `${api}/recovery/:path*` },
      { source: '/parent/:path*', destination: `${api}/parent/:path*` },
      { source: '/users/:path*', destination: `${api}/users/:path*` },
      { source: '/agents/:path*', destination: `${api}/agents/:path*` },
      { source: '/gamification/:path*', destination: `${api}/gamification/:path*` },
    ]
  },
}

module.exports = withNextIntl(nextConfig)
