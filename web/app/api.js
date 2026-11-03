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

// Send a question (the race engineer): never kept, every question is asked again.
export async function post(path, body) {
  const response = await fetch("/api" + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const answer = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof answer.detail === "string" ? answer.detail : response.statusText;
    throw new Error(`${response.status} · ${detail}`);
  }
  return answer;
}

// "/weekends/2024/1": the start of every address about one weekend
export const weekendPath = (c) => `/weekends/${c.season}/${c.round}`;
