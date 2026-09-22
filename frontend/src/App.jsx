import { useState, useEffect } from 'react';
import './App.css';
import JobList from './components/JobList';
import JobDetail from './components/JobDetail';
import SubmitJob from './components/SubmitJob';
import Sidebar from './components/Sidebar';
import { fetchJobs, fetchJob, fetchStats } from './api';

function App() {
  const [view, setView] = useState('list');
  const [jobs, setJobs] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(0);
  const [selectedJob, setSelectedJob] = useState(null);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({
    total_count: 0,
    pending: 0,
    running: 0,
    completed: 0,
    failed: 0,
    retrying: 0,
  });

  const pageSize = 50;

  // Load jobs when page changes
  useEffect(() => {
    const loadJobs = async () => {
      try {
        setLoading(true);
        const offset = currentPage * pageSize;
        const data = await fetchJobs(pageSize, offset);
        setJobs(data.jobs);
        setTotalCount(data.total_count);
      } catch (error) {
        console.error('Failed to fetch jobs:', error);
      } finally {
        setLoading(false);
      }
    };

    loadJobs();
  }, [currentPage, pageSize]);

  // Load stats periodically
  useEffect(() => {
    const loadStats = async () => {
      try {
        const data = await fetchStats();
        setStats(data);
      } catch (error) {
        console.error('Failed to fetch stats:', error);
      }
    };

    loadStats();
    const interval = setInterval(loadStats, 3000); // Update every 3 seconds
    return () => clearInterval(interval);
  }, []);

  const handleSelectJob = async (jobId) => {
    try {
      const job = await fetchJob(jobId);
      setSelectedJob(job);
      setView('detail');
    } catch (error) {
      console.error('Failed to fetch job:', error);
    }
  };

  const handleJobSubmitted = () => {
    setView('list');
    setCurrentPage(0);
  };

  const handleBack = () => {
    setSelectedJob(null);
    setView('list');
  };

  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="app">
      <Sidebar
        stats={stats}
        currentView={view}
        onNavigate={setView}
      />
      <main className="main-content">
        {view === 'submit' && (
          <SubmitJob onSuccess={handleJobSubmitted} />
        )}
        {view === 'list' && (
          <JobList
            jobs={jobs}
            loading={loading}
            onSelectJob={handleSelectJob}
            onSubmitNew={() => setView('submit')}
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={setCurrentPage}
          />
        )}
        {view === 'detail' && selectedJob && (
          <JobDetail job={selectedJob} onBack={handleBack} />
        )}
      </main>
    </div>
  );
}

export default App;