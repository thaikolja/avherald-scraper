export default defineAppConfig({
  header: {
    title: 'The Aviation Herald Scraper',
    logo: {
      light: '/logo-light.svg',
      dark: '/logo-dark.svg',
      alt: 'The Aviation Herald Scraper',
    },
  },
  socials: {
    gitlab: 'https://gitlab.com/thaikolja/avherald-scraper',
    github: 'https://github.com/thaikolja/avherald-scraper',
  },
  github: {
    url: 'https://gitlab.com/thaikolja/avherald-scraper/-',
    branch: 'main',
    rootDir: 'docs',
  },
  seo: {
    titleTemplate: '%s · The Aviation Herald Scraper',
  },
  toc: {
    bottom: {
      links: [
        {
          icon: 'i-lucide-heart',
          label: 'Donate',
          to: '/project/donate',
        },
      ],
    },
  },
  ui: {
    colors: {
      primary: 'zinc',
      neutral: 'zinc',
    },
  },
})
