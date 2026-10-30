import { defineNuxtConfig } from 'nuxt/config'

const siteUrl = process.env.NUXT_PUBLIC_SITE_URL || 'https://thaikolja.gitlab.io'

export default defineNuxtConfig({
  extends: [ 'docus' ],
  docus:   {
    assistant: {
      enabled: false
    }
  },
  site:    {
    url:  siteUrl,
    name: 'The Aviation Herald Scraper'
  },
  robots:  {
    robotsTxt: false
  },
  image:   {
    provider: 'none'
  },
  nitro:   {
    rollupConfig: {
      onwarn(warning, warn) {
        if (warning.code === 'INVALID_ANNOTATION') return
        warn(warning)
      }
    }
  },
  app:     {
    head: {
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }
      ]
    }
  }
})
