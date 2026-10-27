// The only file that talks to the server. Every window asks for its data through get().
// Answers are kept in memory, so ten windows asking for the same table cost one request.

const cache = new Map();

export function get(path) {
  if (!cache.has(path)) {
    const answer = fetch("/api" + path).then(async (response) => {
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        const detail = typeof body.detail === "string" ? body.detail : response.statusText;
        throw new Error(`${response.status} · ${detail} (GET /api${path})`);
      }
      return response.json();
    });
    answer.catch(() => cache.delete(path)); // a failed answer is forgotten, so a retry asks again
    cache.set(path, answer);
  }
  return cache.get(path);
}

// "/weekends/2024/1": the start of every address about one weekend
export const weekendPath = (c) => `/weekends/${c.season}/${c.round}`;
