// Retry policy for polling: network errors, 5xx and 429 only; other 4xx surface at once.
export function isRetryable(err) {
  const status = err && err.status;
  if (status === undefined || status === null) return true;
  return status >= 500 || status === 429;
}
