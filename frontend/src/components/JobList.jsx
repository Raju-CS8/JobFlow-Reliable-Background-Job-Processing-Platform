import '../styles/JobList.css';

function JobList({ jobs, loading, onSelectJob, onSubmitNew, currentPage, totalPages, onPageChange }) {
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

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  return (
    <div className="job-list-container">
      <div className="list-header">
        <h2>Jobs</h2>
        <button className="btn-primary" onClick={onSubmitNew}>
          + New Job
        </button>
      </div>

      {loading && <div className="loading">Loading...</div>}

      {!loading && jobs.length === 0 && (
        <div className="empty-state">
          <p>No jobs found</p>
          <button className="btn-primary" onClick={onSubmitNew}>
            Submit your first job
          </button>
        </div>
      )}

      {!loading && jobs.length > 0 && (
        <>
          <div className="jobs-table">
            <div className="table-header">
              <div className="col-id">Job ID</div>
              <div className="col-type">Type</div>
              <div className="col-status">Status</div>
              <div className="col-priority">Priority</div>
              <div className="col-created">Created</div>
            </div>
            {jobs.map((job) => (
              <div
                key={job.id}
                className="table-row"
                onClick={() => onSelectJob(job.id)}
              >
                <div className="col-id">
                  <code>{job.id.substring(0, 8)}...</code>
                </div>
                <div className="col-type">{job.job_type}</div>
                <div className="col-status">
                  <span className={`status-badge ${getStatusColor(job.status)}`}>
                    {job.status}
                  </span>
                </div>
                <div className="col-priority">
                  <span className="priority-badge">{job.priority}</span>
                </div>
                <div className="col-created">
                  {formatDate(job.created_at)}
                </div>
              </div>
            ))}
          </div>

          <div className="pagination">
            <button
              className="pagination-btn"
              onClick={() => onPageChange(currentPage - 1)}
              disabled={currentPage === 0}
            >
              ← Previous
            </button>
            
            <div className="pagination-info">
              Page {currentPage + 1} of {totalPages}
            </div>
            
            <button
              className="pagination-btn"
              onClick={() => onPageChange(currentPage + 1)}
              disabled={currentPage >= totalPages - 1}
            >
              Next →
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export default JobList;