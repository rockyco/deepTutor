/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },
  // For Cloudflare Pages deployment
  images: {
    unoptimized: true,
  },
};

module.exports = nextConfig;
