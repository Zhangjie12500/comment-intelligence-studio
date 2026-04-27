const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8010/api';

export async function createJob(payload) {
  const res = await fetch(`${BASE_URL}/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Failed to create job: ${res.status} ${text}`);
  }
  return res.json();
}

export async function getJob(jobId) {
  const res = await fetch(`${BASE_URL}/jobs/${jobId}`);
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Failed to get job: ${res.status} ${text}`);
  }
  return res.json();
}

export function getFileUrl(jobId, taskId, type) {
  return `${BASE_URL}/jobs/${jobId}/${taskId}/${type}`;
}
