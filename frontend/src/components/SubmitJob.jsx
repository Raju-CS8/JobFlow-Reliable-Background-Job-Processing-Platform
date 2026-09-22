import { useState } from 'react';
import { submitJob } from '../api';
import '../styles/SubmitJob.css';

function SubmitJob({ onSuccess }) {
  const [formData, setFormData] = useState({
    orders: [{ order_id: '', amount: '', currency: 'INR', status: 'PAID' }],
    priority: 'NORMAL',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const handleOrderChange = (index, field, value) => {
    const newOrders = [...formData.orders];
    newOrders[index][field] = value;
    setFormData({ ...formData, orders: newOrders });
  };

  const addOrder = () => {
    setFormData({
      ...formData,
      orders: [
        ...formData.orders,
        { order_id: '', amount: '', currency: 'INR', status: 'PAID' },
      ],
    });
  };

  const removeOrder = (index) => {
    if (formData.orders.length > 1) {
      const newOrders = formData.orders.filter((_, i) => i !== index);
      setFormData({ ...formData, orders: newOrders });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);

    try {
      const payload = {
        orders: formData.orders.map((order) => ({
          ...order,
          amount: parseFloat(order.amount),
        })),
      };

      await submitJob(
        'order_reconciliation',
        payload,
        formData.priority,
        3
      );

      setSuccess('Job submitted successfully!');
      setFormData({
        orders: [{ order_id: '', amount: '', currency: 'INR', status: 'PAID' }],
        priority: 'NORMAL',
      });

      setTimeout(() => {
        onSuccess();
      }, 1000);
    } catch (err) {
      setError('Failed to submit job: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="submit-job-container">
      <div className="form-header">
        <h2>Submit New Job</h2>
        <p>Order Reconciliation Job</p>
      </div>

      {error && <div className="alert error">{error}</div>}
      {success && <div className="alert success">{success}</div>}

      <form onSubmit={handleSubmit} className="submit-form">
        <section className="form-section">
          <h3>Priority</h3>
          <div className="form-group">
            <select
              value={formData.priority}
              onChange={(e) =>
                setFormData({ ...formData, priority: e.target.value })
              }
              className="select-input"
            >
              <option value="LOW">Low</option>
              <option value="NORMAL">Normal</option>
              <option value="HIGH">High</option>
            </select>
          </div>
        </section>

        <section className="form-section">
          <h3>Orders</h3>
          {formData.orders.map((order, index) => (
            <div key={index} className="order-card">
              <div className="order-number">Order {index + 1}</div>
              
              <div className="form-row">
                <div className="form-group">
                  <label>Order ID</label>
                  <input
                    type="text"
                    placeholder="ORD-1"
                    value={order.order_id}
                    onChange={(e) =>
                      handleOrderChange(index, 'order_id', e.target.value)
                    }
                    required
                    className="text-input"
                  />
                </div>
                <div className="form-group">
                  <label>Amount</label>
                  <input
                    type="number"
                    placeholder="49.99"
                    value={order.amount}
                    onChange={(e) =>
                      handleOrderChange(index, 'amount', e.target.value)
                    }
                    step="0.01"
                    required
                    className="text-input"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Currency</label>
                  <select
                    value={order.currency}
                    onChange={(e) =>
                      handleOrderChange(index, 'currency', e.target.value)
                    }
                    className="select-input"
                  >
                    <option value="INR">INR</option>
                    <option value="USD">USD</option>
                    <option value="EUR">EUR</option>
                    <option value="GBP">GBP</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Status</label>
                  <select
                    value={order.status}
                    onChange={(e) =>
                      handleOrderChange(index, 'status', e.target.value)
                    }
                    className="select-input"
                  >
                    <option value="PENDING">Pending</option>
                    <option value="PAID">Paid</option>
                    <option value="FAILED">Failed</option>
                    <option value="REFUNDED">Refunded</option>
                  </select>
                </div>
              </div>

              {formData.orders.length > 1 && (
                <button
                  type="button"
                  className="btn-remove"
                  onClick={() => removeOrder(index)}
                >
                  Remove Order
                </button>
              )}
            </div>
          ))}

          <button
            type="button"
            className="btn-secondary"
            onClick={addOrder}
          >
            + Add Order
          </button>
        </section>

        <div className="form-actions">
          <button
            type="submit"
            className="btn-primary btn-large"
            disabled={loading}
          >
            {loading ? 'Submitting...' : 'Submit Job'}
          </button>
        </div>
      </form>
    </div>
  );
}

export default SubmitJob;