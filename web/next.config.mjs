/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The web app consumes the SAME Django API as the Flutter app (v2 §8).
  // In dev we proxy /api → Django so cookies/CORS stay simple; in production
  // nginx serves both from lms.centrefocus.ma.
  async rewrites() {
    const backend = process.env.API_ORIGIN || 'http://127.0.0.1:8000';
    return [{ source: '/api/:path*', destination: `${backend}/api/:path*` }];
  },
  images: { remotePatterns: [{ protocol: 'https', hostname: '**' }] },
};

export default nextConfig;
