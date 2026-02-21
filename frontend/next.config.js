/** @type {import('next').NextConfig} */
const nextConfig = {
  // We will proxy requests to the backend
  rewrites: async () => {
    return [
      {
        source: '/api/:path*',
        destination: (process.env.BACKEND_URL || 'http://localhost:8000') + '/api/:path*',
      },
    ]
  },
}

module.exports = nextConfig
