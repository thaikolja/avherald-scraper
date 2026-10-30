const UPSTREAM_ORIGIN = 'https://thaikolja.github.io'
const PREFIX = '/avherald-scraper'

export default {
  async fetch(request) {
    const incoming = new URL(request.url)

    if (incoming.pathname === '/' || incoming.pathname === '') {
      return Response.redirect(`${incoming.origin}${PREFIX}/`, 302)
    }

    if (incoming.pathname !== PREFIX && !incoming.pathname.startsWith(`${PREFIX}/`)) {
      return new Response('Not found', { status: 404 })
    }

    const upstream = new URL(`${incoming.pathname}${incoming.search}`, UPSTREAM_ORIGIN)
    const headers = new Headers(request.headers)
    headers.set('host', upstream.host)
    headers.delete('cookie')

    const response = await fetch(upstream, {
      method: request.method,
      headers,
      redirect: 'manual',
    })

    const location = response.headers.get('location')
    if (location && response.status >= 300 && response.status < 400) {
      const redirected = new URL(location, upstream)
      if (redirected.hostname === upstream.hostname) {
        redirected.protocol = incoming.protocol
        redirected.host = incoming.host
        return Response.redirect(redirected.toString(), response.status)
      }
    }

    const outgoing = new Headers(response.headers)
    outgoing.delete('set-cookie')
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: outgoing,
    })
  },
}
