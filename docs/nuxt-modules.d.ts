import type { ModuleOptions as ImageOptions } from '@nuxt/image'
import type { ModuleOptions as RobotsOptions } from '@nuxtjs/robots'
import type { ModuleOptions as SiteOptions } from 'nuxt-site-config'

declare module '@nuxt/schema' {
  interface NuxtConfig {
    image?: Partial<ImageOptions> | false
    robots?: Partial<RobotsOptions> | false
    site?: Partial<SiteOptions> | false
  }
}

declare module 'nuxt/schema' {
  interface NuxtConfig {
    image?: Partial<ImageOptions> | false
    robots?: Partial<RobotsOptions> | false
    site?: Partial<SiteOptions> | false
  }
}

export {}
