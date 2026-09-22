"""Order reconciliation processor with comprehensive validation."""

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List
from dataclasses import dataclass

from jobflow.domain.exceptions import PermanentError


@dataclass
class ValidationRule:
    """A validation rule with name and check function."""
    name: str
    check: callable
    error_message: str


class ValidationError(PermanentError):
    """Raised when validation fails permanently."""
    pass


class OrderValidator:
    """Validates orders with explicit, testable rules."""

    VALID_CURRENCIES = {'INR', 'USD', 'EUR', 'GBP'}
    VALID_STATUSES = {'PENDING', 'PAID', 'FAILED', 'REFUNDED'}

    MIN_AMOUNT = Decimal('0.01')
    MAX_AMOUNT = Decimal('999999999.99')

    @classmethod
    def validate_order(cls, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a single order.

        Raises:
            ValidationError: If the order fails validation.
        """

        # Safely reject non-dictionary records
        if not isinstance(order, dict):
            raise ValidationError("order must be a dictionary")

        issues = []

        # ---------------------------------------------------------
        # Rule 1: Required order_id
        # ---------------------------------------------------------
        if 'order_id' not in order:
            issues.append("missing required fields: order_id")
        elif not isinstance(order.get('order_id'), str):
            issues.append("order_id must be a non-empty string")
        elif not order['order_id'].strip():
            issues.append("order_id cannot be empty")

        # ---------------------------------------------------------
        # Rule 2: Required amount
        # ---------------------------------------------------------
        if 'amount' not in order:
            issues.append("missing required fields: amount")
            amount = None
        else:
            raw_amount = order['amount']

            try:
                amount = Decimal(str(raw_amount))
            except (TypeError, ValueError, InvalidOperation):
                issues.append(
                    f"amount must be a valid number, "
                    f"got {type(raw_amount).__name__}"
                )
                amount = None

        if amount is not None:
            if amount <= 0:
                issues.append(
                    f"amount must be positive, got {amount}"
                )
            elif amount > cls.MAX_AMOUNT:
                issues.append(
                    f"amount must be <= {cls.MAX_AMOUNT}, got {amount}"
                )

        # ---------------------------------------------------------
        # Rule 3: Currency
        # ---------------------------------------------------------
        if 'currency' not in order:
            issues.append("missing required fields: currency")
        else:
            raw_currency = order.get('currency')

            if not isinstance(raw_currency, str):
                currency = ''
            else:
                currency = raw_currency.upper()

            if not currency:
                issues.append("currency is required")
            elif currency not in cls.VALID_CURRENCIES:
                issues.append(
                    f"unsupported currency '{currency}'. "
                    f"Allowed values: "
                    f"{', '.join(sorted(cls.VALID_CURRENCIES))}"
                )

        # ---------------------------------------------------------
        # Rule 4: Status
        # ---------------------------------------------------------
        if 'status' not in order:
            issues.append("missing required fields: status")
        else:
            raw_status = order.get('status')

            if not isinstance(raw_status, str):
                status = ''
            else:
                status = raw_status.upper()

            if not status:
                issues.append("status is required")
            elif status not in cls.VALID_STATUSES:
                issues.append(
                    f"unsupported status '{status}'. "
                    f"Allowed values: "
                    f"{', '.join(sorted(cls.VALID_STATUSES))}"
                )

        # ---------------------------------------------------------
        # Final validation result
        # ---------------------------------------------------------
        if issues:
            raise ValidationError("; ".join(issues))

        return order

    @classmethod
    def validate_orders_batch(
        cls,
        orders: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Validate a batch of orders.

        Raises:
            ValidationError: If an order fails validation.
        """

        validated = []

        for i, order in enumerate(orders):
            try:
                validated.append(cls.validate_order(order))
            except ValidationError as e:
                raise ValidationError(
                    f"Order {i}: {str(e)}"
                )

        return validated


class OrderReconciliationProcessor:
    """
    Processes order reconciliation jobs.

    Responsibility:
        Validate orders and return reconciliation summary.

    Deterministic:
        Same input always produces the same output.

    Idempotent:
        Can be safely re-executed without side effects.
    """

    @staticmethod
    def process(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process order reconciliation.

        Returns:
            Summary containing counts, total amount and issues.

        Raises:
            PermanentError:
                If the overall payload structure is invalid.
        """

        # ---------------------------------------------------------
        # Validate payload structure
        # ---------------------------------------------------------
        if not isinstance(payload, dict):
            raise PermanentError(
                "Payload must be a dictionary"
            )

        if 'orders' not in payload:
            raise PermanentError(
                "Payload must contain 'orders' key"
            )

        orders = payload['orders']

        if not isinstance(orders, list):
            raise PermanentError(
                f"orders must be a list, "
                f"got {type(orders).__name__}"
            )

        # Empty batch is valid
        if not orders:
            return {
                'total_records': 0,
                'valid_count': 0,
                'invalid_count': 0,
                'valid_total_amount': 0.0,
                'issues': [],
            }

        # ---------------------------------------------------------
        # Validate each order independently
        # ---------------------------------------------------------
        validated_orders = []
        issues = []

        for index, order in enumerate(orders):
            try:
                validated_order = OrderValidator.validate_order(order)

                validated_orders.append(
                    (index, validated_order)
                )

            except ValidationError as e:
                issues.append(
                    f"Order {index}: {str(e)}"
                )

        # ---------------------------------------------------------
        # Handle duplicate order IDs
        #
        # First occurrence remains valid.
        # Later occurrences are marked invalid.
        # ---------------------------------------------------------
        seen_order_ids = set()
        unique_valid_orders = []

        duplicate_ids = []

        for index, order in validated_orders:
            order_id = order['order_id']

            if order_id in seen_order_ids:
                duplicate_ids.append(order_id)

                issues.append(
                    f"Order {index}: duplicate order ID '{order_id}'"
                )
            else:
                seen_order_ids.add(order_id)
                unique_valid_orders.append(order)

        # ---------------------------------------------------------
        # Calculate final counts
        # ---------------------------------------------------------
        valid_count = len(unique_valid_orders)

        invalid_count = len(orders) - valid_count

        # ---------------------------------------------------------
        # Calculate total amount only from valid orders
        # ---------------------------------------------------------
        total_amount = sum(
            Decimal(str(order['amount']))
            for order in unique_valid_orders
        )

        return {
            'total_records': len(orders),
            'valid_count': valid_count,
            'invalid_count': invalid_count,
            'valid_total_amount': float(total_amount),
            'issues': issues,
        }