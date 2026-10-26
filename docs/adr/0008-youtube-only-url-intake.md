# 0008 YouTube-only URL intake

## Context

`POST /api/generate` passes a user-supplied URL to beat-analyser, which downloads it with yt-dlp. A downloader that accepts any URL can be pointed at internal addresses (server-side request forgery) or at hosts the service has no reason to contact. The service is local and unauthenticated, so a malicious web page could also try to trigger requests to it.

## Decision

1. saber-tooth accepts only `http` and `https` URLs whose host is exactly one of `youtube.com`, `www.youtube.com`, `m.youtube.com`, `music.youtube.com` and `youtu.be`.
2. URLs with userinfo, a malformed port, spaces, backslashes or non-printable characters are refused with 400.
3. beat-analyser validates again on its side and derives the project name from the video id. The check is defence in depth, not the only barrier.
4. Requests that change state and carry a mismatching `Origin` header are refused with 403.
5. Uploads are limited in size (413) and to audio extensions (415).

## Consequences

1. Other video sites are not supported without changing this list.
2. The SSRF review covers the intake path: no user text reaches a network call except a validated YouTube host.
3. Hosts must match exactly, so look-alike names and subdomain tricks are refused.
