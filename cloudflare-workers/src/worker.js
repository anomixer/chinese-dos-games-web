export default {
  async fetch(request, env) {
    const url = new URL(request.url)

    // /stream/<id>.zip => 代理到 REMOTE_PREFIX/<id>.zip
    if (url.pathname.startsWith('/stream/')) {
      const idEncoded = url.pathname.replace(/^\/stream\//, '').replace(/\.zip$/, '')
      const id = decodeURIComponent(idEncoded)
      const upstream = `${env.REMOTE_PREFIX}${encodeURIComponent(id)}.zip`

      const headers = new Headers()
      const range = request.headers.get('Range')
      if (range) headers.set('Range', range)

      const upstreamResp = await fetch(upstream, { method: 'GET', headers })

      // 傳回選定標頭，維持串流/分段特性
      const passHeaders = [
        'Content-Length',
        'Content-Range',
        'Accept-Ranges',
        'Last-Modified',
        'ETag',
        'Cache-Control',
        'Content-Type'
      ]
      const respHeaders = new Headers()
      passHeaders.forEach(h => {
        const v = upstreamResp.headers.get(h)
        if (v) respHeaders.set(h, v)
      })

      return new Response(upstreamResp.body, { status: upstreamResp.status, headers: respHeaders })
    }

    // 其他路徑：若設定了 ORIGIN，則反向代理到你的 Flask 站台
    if (env.ORIGIN) {
      const originURL = new URL(env.ORIGIN)
      const forwardURL = `${originURL.origin}${url.pathname}${url.search}`
      return fetch(forwardURL, request)
    }

    return new Response('Not found', { status: 404 })
  }
}
