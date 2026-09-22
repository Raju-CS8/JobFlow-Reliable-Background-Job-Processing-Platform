"""Tests for job processors."""

import pytest
from jobflow.processors.order_reconciliation import OrderReconciliationProcessor
from jobflow.domain.exceptions import PermanentError, RetryableError


class TestOrderReconciliationProcessor:
    """Test the order reconciliation processor."""
    
    def test_process_valid_single_order(self):
        """Test processing a single valid order."""
        payload = {
            "orders": [
                {
                    "order_id": "ORD-1",
                    "amount": 49.99,
                    "currency": "INR",
                    "status": "PAID",
                }
            ]
        }
        
        result = OrderReconciliationProcessor.process(payload)
        
        assert result["total_records"] == 1
        assert result["valid_count"] == 1
        assert result["invalid_count"] == 0
        assert result["valid_total_amount"] == 49.99
        assert result["issues"] == []
    
    def test_process_multiple_valid_orders(self):
        """Test processing multiple valid orders."""
        payload = {
            "orders": [
                {
                    "order_id": "ORD-1",
                    "amount": 49.99,
                    "currency": "USD",
                    "status": "PAID",
                },
                {
                    "order_id": "ORD-2",
                    "amount": 99.50,
                    "currency": "EUR",
                    "status": "PENDING",
                },
                {
                    "order_id": "ORD-3",
                    "amount": 25.00,
                    "currency": "GBP",
                    "status": "REFUNDED",
                },
            ]
        }
        
        result = OrderReconciliationProcessor.process(payload)
        
        assert result["total_records"] == 3
        assert result["valid_count"] == 3
        assert result["invalid_count"] == 0
        assert result["valid_total_amount"] == 49.99 + 99.50 + 25.00
        assert result["issues"] == []
    
    def test_process_with_duplicate_order_ids(self):
        """Test that duplicate order IDs are rejected."""
        payload = {
            "orders": [
                {
                    "order_id": "ORD-1",
                    "amount": 49.99,
                    "currency": "INR",
                    "status": "PAID",
                },
                {
                    "order_id": "ORD-1",  # Duplicate
                    "amount": 29.99,
                    "currency": "INR",
                    "status": "PAID",
                },
            ]
        }
        
        result = OrderReconciliationProcessor.process(payload)
        
        assert result["total_records"] == 2
        assert result["valid_count"] == 1
        assert result["invalid_count"] == 1
        assert result["valid_total_amount"] == 49.99
        assert len(result["issues"]) == 1
        assert "duplicate" in result["issues"][0].lower()
    
    def test_process_invalid_amount_negative(self):
        """Test that negative amounts are rejected."""
        payload = {
            "orders": [
                {
                    "order_id": "ORD-1",
                    "amount": -10.00,
                    "currency": "INR",
                    "status": "PAID",
                }
            ]
        }
        
        result = OrderReconciliationProcessor.process(payload)
        
        assert result["valid_count"] == 0
        assert result["invalid_count"] == 1
        assert "positive" in result["issues"][0].lower()
    
    def test_process_invalid_amount_zero(self):
        """Test that zero amount is rejected."""
        payload = {
            "orders": [
                {
                    "order_id": "ORD-1",
                    "amount": 0,
                    "currency": "INR",
                    "status": "PAID",
                }
            ]
        }
        
        result = OrderReconciliationProcessor.process(payload)
        
        assert result["valid_count"] == 0
        assert result["invalid_count"] == 1
        assert "positive" in result["issues"][0].lower()
    
    def test_process_invalid_amount_non_numeric(self):
        """Test that non-numeric amounts are rejected."""
        payload = {
            "orders": [
                {
                    "order_id": "ORD-1",
                    "amount": "not_a_number",
                    "currency": "INR",
                    "status": "PAID",
                }
            ]
        }
        
        result = OrderReconciliationProcessor.process(payload)
        
        assert result["valid_count"] == 0
        assert result["invalid_count"] == 1
        assert "valid number" in result["issues"][0].lower()
    
    def test_process_unsupported_currency(self):
        """Test that unsupported currencies are rejected."""
        payload = {
            "orders": [
                {
                    "order_id": "ORD-1",
                    "amount": 49.99,
                    "currency": "JPY",
                    "status": "PAID",
                }
            ]
        }
        
        result = OrderReconciliationProcessor.process(payload)
        
        assert result["valid_count"] == 0
        assert result["invalid_count"] == 1
        assert "unsupported currency" in result["issues"][0].lower()
    
    def test_process_unsupported_status(self):
        """Test that unsupported statuses are rejected."""
        payload = {
            "orders": [
                {
                    "order_id": "ORD-1",
                    "amount": 49.99,
                    "currency": "INR",
                    "status": "PROCESSING",
                }
            ]
        }
        
        result = OrderReconciliationProcessor.process(payload)
        
        assert result["valid_count"] == 0
        assert result["invalid_count"] == 1
        assert "unsupported status" in result["issues"][0].lower()
    
    def test_process_missing_order_id(self):
        """Test that missing order_id is rejected."""
        payload = {
            "orders": [
                {
                    "amount": 49.99,
                    "currency": "INR",
                    "status": "PAID",
                }
            ]
        }
        
        result = OrderReconciliationProcessor.process(payload)
        
        assert result["valid_count"] == 0
        assert result["invalid_count"] == 1
        assert "missing required fields" in result["issues"][0].lower()
    
    def test_process_missing_amount(self):
        """Test that missing amount is rejected."""
        payload = {
            "orders": [
                {
                    "order_id": "ORD-1",
                    "currency": "INR",
                    "status": "PAID",
                }
            ]
        }
        
        result = OrderReconciliationProcessor.process(payload)
        
        assert result["valid_count"] == 0
        assert result["invalid_count"] == 1
        assert "missing required fields" in result["issues"][0].lower()
    
    def test_process_empty_orders_list(self):
        """Test processing with empty orders list."""
        payload = {"orders": []}
        
        result = OrderReconciliationProcessor.process(payload)
        
        assert result["total_records"] == 0
        assert result["valid_count"] == 0
        assert result["invalid_count"] == 0
        assert result["valid_total_amount"] == 0.0
        assert result["issues"] == []
    
    def test_process_mixed_valid_and_invalid(self):
        """Test processing a mix of valid and invalid orders."""
        payload = {
            "orders": [
                {
                    "order_id": "ORD-1",
                    "amount": 49.99,
                    "currency": "INR",
                    "status": "PAID",
                },
                {
                    "order_id": "ORD-2",
                    "amount": -10.00,
                    "currency": "INR",
                    "status": "PAID",
                },
                {
                    "order_id": "ORD-3",
                    "amount": 100.00,
                    "currency": "USD",
                    "status": "PENDING",
                },
                {
                    "order_id": "ORD-4",
                    "amount": "invalid",
                    "currency": "INR",
                    "status": "PAID",
                },
            ]
        }
        
        result = OrderReconciliationProcessor.process(payload)
        
        assert result["total_records"] == 4
        assert result["valid_count"] == 2
        assert result["invalid_count"] == 2
        assert result["valid_total_amount"] == 49.99 + 100.00
        assert len(result["issues"]) == 2
    
    def test_process_missing_orders_field(self):
        """Test that missing 'orders' field raises PermanentError."""
        payload = {"data": []}
        
        with pytest.raises(PermanentError):
            OrderReconciliationProcessor.process(payload)
    
    def test_process_invalid_payload_not_dict(self):
        """Test that non-dict payload raises PermanentError."""
        with pytest.raises(PermanentError):
            OrderReconciliationProcessor.process([])
    
    def test_process_orders_not_list(self):
        """Test that non-list 'orders' raises PermanentError."""
        payload = {"orders": "not_a_list"}
        
        with pytest.raises(PermanentError):
            OrderReconciliationProcessor.process(payload)
    
    def test_process_order_not_dict(self):
        """Test that non-dict order record is rejected."""
        payload = {
            "orders": [
                "not_a_dict"
            ]
        }
        
        result = OrderReconciliationProcessor.process(payload)
        
        assert result["valid_count"] == 0
        assert result["invalid_count"] == 1
        assert "must be a dictionary" in result["issues"][0].lower()
    
    def test_process_idempotent(self):
        """Test that processing the same payload twice produces the same result."""
        payload = {
            "orders": [
                {
                    "order_id": "ORD-1",
                    "amount": 49.99,
                    "currency": "INR",
                    "status": "PAID",
                },
                {
                    "order_id": "ORD-2",
                    "amount": 29.99,
                    "currency": "USD",
                    "status": "PENDING",
                },
            ]
        }
        
        result1 = OrderReconciliationProcessor.process(payload)
        result2 = OrderReconciliationProcessor.process(payload)
        
        assert result1 == result2
    
    def test_process_with_decimal_amounts(self):
        """Test that decimal amounts are handled correctly."""
        payload = {
            "orders": [
                {
                    "order_id": "ORD-1",
                    "amount": 10.55,
                    "currency": "INR",
                    "status": "PAID",
                },
                {
                    "order_id": "ORD-2",
                    "amount": 20.45,
                    "currency": "INR",
                    "status": "PAID",
                },
            ]
        }
        
        result = OrderReconciliationProcessor.process(payload)
        
        assert result["valid_count"] == 2
        assert result["valid_total_amount"] == 31.00