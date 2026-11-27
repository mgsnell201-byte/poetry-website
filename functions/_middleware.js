/**
 * Redirect www.osmoticpoet.com permanently (301) to the apex domain
 * osmoticpoet.com so search engines only index one canonical hostname.
 */
export async function onRequest(context) {
  const url = new URL(context.request.url);
  if (url.hostname === 'www.osmoticpoet.com') {
    url.hostname = 'osmoticpoet.com';
    return Response.redirect(url.toString(), 301);
  }
  return context.next();
}
