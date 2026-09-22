import '../styles/JobDetail.css';

function JobDetail({ job, onBack }) {
  const formatDate = (dateString) => {
    if (!dateString) return '—';
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'PENDING':
        return 'status-pending';
      case 'RUNNING':
        return 'status-running';
      case 'COMPLETED':
        return 'status-completed';
      case 'FAILED':
        return 'status-failed';
      case 'RETRYING':
        return 'status-retrying';
      default:
        return '';
    }
  };

  const getDuration = () => {
    if (!job.started_at) return null;
    const end = job.completed_at || new Date();
    const start = new Date(job.started_at);
    const seconds = Math.round((end - start) / 1000);
    return `${seconds}s`;
  };

  return (
    <div className="job-detail-container">
      <div className="detail-header">
        <button className="btn-back" onClick={onBack}>
          ← Back
        </button>
        <h2>Job Details</h2>
      </div>

      <div className="detail-content">
        <section className="detail-section">
          <h3>Overview</h3>
          <div className="detail-grid">
            <div className="detail-item">
              <label>Job ID</label>
              <code className="job-id">{job.id}</code>
            </div>
            <div className="detail-item">
              <label>Type</label>
              <p>{job.job_type}</p>
            </div>
            <div className="detail-item">
              <label>Status</label>
              <span className={`status-badge ${getStatusColor(job.status)}`}>
                {job.status}
              </span>
            </div>
            <div className="detail-item">
              <label>Priority</label>
              <p>{job.priority}</p>
            </div>
          </div>
        </section>

        <section className="detail-section">
          <h3>Timing</h3>
          <div className="detail-grid">
            <div className="detail-item">
              <label>Created</label>
              <p>{formatDate(job.created_at)}</p>
            </div>
            <div className="detail-item">
              <label>Started</label>
              <p>{formatDate(job.started_at)}</p>
            </div>
            <div className="detail-item">
              <label>Completed</label>
              <p>{formatDate(job.completed_at)}</p>
            </div>
            {getDuration() && (
              <div className="detail-item">
                <label>Duration</label>
                <p>{getDuration()}</p>
              </div>
            )}
          </div>
        </section>

        <section className="detail-section">
          <h3>Attempts</h3>
          <div className="detail-grid">
            <div className="detail-item">
              <label>Current Attempt</label>
              <p>{job.attempt_count + 1} of {job.max_attempts}</p>
            </div>
            {job.next_attempt_at && (
              <div className="detail-item">
                <label>Next Attempt At</label>
                <p>{formatDate(job.next_attempt_at)}</p>
              </div>
            )}
            {job.claimed_by && (
              <div className="detail-item">
                <label>Claimed By</label>
                <code>{job.claimed_by}</code>
              </div>
            )}
          </div>
        </section>

        {job.payload && (
          <section className="detail-section">
            <h3>Payload</h3>
            <pre className="json-block">
              {JSON.stringify(job.payload, null, 2)}
            </pre>
          </section>
        )}

        {job.result && (
          <section className="detail-section success">
            <h3>Result</h3>
            <pre className="json-block">
              {JSON.stringify(job.result, null, 2)}
            </pre>
          </section>
        )}

        {job.error && (
          <section className="detail-section error">
            <h3>Error</h3>
            <p className="error-message">{job.error}</p>
          </section>
        )}
      </div>
    </div>
  );
}

export default JobDetail;