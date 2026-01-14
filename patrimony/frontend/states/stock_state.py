import reflex as rx

from ...backend.api.stock_api import add_stock_position, validate_price, validate_ticker


class AddStockState(rx.State):
    """State for the add stock dialog."""

    # Form fields
    ticker: str = ""
    buy_price: float = 0.01
    quantity: float = 1.0

    # UI state
    is_open: bool = False
    is_loading: bool = False

    # Feedback
    error_message: str = ""
    success_message: str = ""

    def _reset_form(self) -> None:
        """Reset form to initial state."""
        self.ticker = ""
        self.buy_price = 0.01
        self.quantity = 1.0
        self.error_message = ""
        self.success_message = ""

    def set_ticker(self, value: str) -> None:
        self.ticker = value.upper()
        self.error_message = ""

    def set_buy_price(self, value: str) -> None:
        try:
            self.buy_price = float(value) if value else 0.01
        except ValueError:
            self.buy_price = 0.01
        self.error_message = ""

    def set_quantity(self, value: str) -> None:
        try:
            self.quantity = float(value) if value else 1.0
        except ValueError:
            self.quantity = 1.0
        self.error_message = ""

    def set_is_open(self, value: bool) -> None:
        self.is_open = value
        if not value:
            self._reset_form()

    def open_dialog(self) -> None:
        self.is_open = True
        self._reset_form()

    def close_dialog(self) -> None:
        self.is_open = False
        self._reset_form()

    async def add_position(self) -> None:
        if not validate_ticker(self.ticker):
            self.error_message = "Please enter a valid ticker symbol"
            return

        if not validate_price(self.buy_price):
            self.error_message = "Please enter a valid price greater than 0"
            return

        self.is_loading = True
        self.error_message = ""

        result = add_stock_position(
            self.ticker,
            self.buy_price,
            self.quantity,
        )

        self.is_loading = False

        if result.success:
            self.success_message = result.message
            self.close_dialog()
        else:
            self.error_message = result.message
