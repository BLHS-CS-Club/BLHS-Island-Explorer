// Runs inside the game when the game is shown on the Play or Try page.
// It copies what the game prints to the page around it, so a mistake in an
// island shows up on screen and not only in the browser console.
(function () {
  if (window.parent === window || window.__blhsHook) return
  window.__blhsHook = true

  function words(value) {
    if (typeof value === 'string') return value
    if (value instanceof Error) return value.message
    try { return JSON.stringify(value) } catch (e) { return String(value) }
  }

  function tell(level, parts) {
    try {
      window.parent.postMessage(
        { from: 'blhs-game', level: level, text: parts.map(words).join(' ') },
        window.location.origin)
    } catch (e) { /* the page around us is gone, nothing to tell */ }
  }

  for (const level of ['log', 'info', 'warn', 'error']) {
    const real = console[level]
    console[level] = function () {
      tell(level, Array.prototype.slice.call(arguments))
      return real.apply(console, arguments)
    }
  }

  window.addEventListener('error', function (e) { tell('error', [e.message || 'error']) })
  window.addEventListener('unhandledrejection', function (e) {
    tell('error', [e.reason && e.reason.message ? e.reason.message : String(e.reason)])
  })

  tell('info', ['[hook] the game page loaded'])
})()
