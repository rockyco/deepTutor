/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  trailingSlash: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "https://deep-tutor-api.fly.dev",
  },
  images: {
    unoptimized: true,
  },
};

module.exports = nextConfig;
