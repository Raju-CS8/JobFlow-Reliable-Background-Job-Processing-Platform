const API_BASE = 'http://localhost:8000';

export async function fetchJobs(limit = 50, offset = 0) {
  const response = await fetch(`${API_BASE}/jobs?limit=${limit}&offset=${offset}`);
  if (!response.ok) {
    throw new Error('Failed to fetch jobs');
  }
  return response.json();
}

export async function fetchJob(jobId) {
  const response = await fetch(`${API_BASE}/jobs/${jobId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch job ${jobId}`);
  }
  return response.json();
}

export async function fetchStats() {
  const response = await fetch(`${API_BASE}/stats`);
  if (!response.ok) {
    throw new Error('Failed to fetch stats');
  }
  return response.json();
}

export async function submitJob(jobType, payload, priority = 'NORMAL', maxAttempts = 3) {
  const response = await fetch(`${API_BASE}/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      job_type: jobType,
      payload,
      priority,
      max_attempts: maxAttempts,
    }),
  });
  if (!response.ok) {
    throw new Error('Failed to submit job');
  }
  return response.json();
}