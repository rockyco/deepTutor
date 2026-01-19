/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },
  // For Cloudflare Pages deployment
  images: {
    unoptimized: true,
  },
  // Required for @cloudflare/next-on-pages
  experimental: {
    runtime: "edge",
  },
};

module.exports = nextConfig;
