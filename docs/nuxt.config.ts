const siteUrl = process.env.NUXT_PUBLIC_SITE_URL || 'https://thaikolja.gitlab.io'

export default defineNuxtConfig({
  site: {
    url: siteUrl,
    name: 'The Aviation Herald Scraper',
  },
  robots: {
    robotsTxt: false,
  },
  image: {
    provider: 'none',
  },
  app: {
    head: {
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
      ],
    },
  },
})
