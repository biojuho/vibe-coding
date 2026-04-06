export class TimeoutError extends Error {
  constructor(message, timeoutMs) {
    super(message);
    this.name = 'TimeoutError';
    this.timeoutMs = timeoutMs;
  }
}

export function isTimeoutError(error) {
  return error instanceof TimeoutError || error?.name === 'TimeoutError';
}

export async function fetchWithTimeout(input, init = {}, options = {}) {
  const timeoutMs = Number.isFinite(options.timeoutMs) ? options.timeoutMs : 10000;
  const message = options.errorMessage || `Request timed out after ${timeoutMs}ms.`;
  const controller = new AbortController();
  const timeoutError = new TimeoutError(message, timeoutMs);
  const timeoutId = setTimeout(() => controller.abort(timeoutError), timeoutMs);

  try {
    return await fetch(input, {
      ...init,
      signal: controller.signal,
    });
  } catch (error) {
    if (error?.name === 'AbortError' || isTimeoutError(error)) {
      throw timeoutError;
    }

    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}
