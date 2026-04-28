const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8010/api';

// Helper to get full URL for file downloads
export function getFullUrl(path) {
  // If path is already absolute, return as is
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  // Otherwise prepend BASE_URL
  return `${BASE_URL}${path.startsWith('/') ? path : '/' + path}`;
}

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
  return getFullUrl(`/jobs/${jobId}/${taskId}/${type}`);
}

// Export BASE_URL for use in components
export { BASE_URL };
