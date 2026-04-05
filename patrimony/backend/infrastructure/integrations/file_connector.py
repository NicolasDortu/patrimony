"""Infrastructure implementation for reading CSV and Excel files."""

import io

import polars as pl

from ...domain.interfaces import FileConnector


class ExcelCsvConnector(FileConnector):
    """Reads CSV and Excel files into polars DataFrames."""

    def read_file(
        self, file_bytes: bytes, filename: str, delimiter: str = ","
    ) -> pl.DataFrame:
        """Parse an uploaded CSV or Excel file.

        Args:
            file_bytes: Raw bytes of the uploaded file.
            filename: Original filename (used to detect format).
            delimiter: Delimiter for CSV files (e.g. ',', ';', '\\t').

        Returns:
            A polars DataFrame with all columns as strings for safe mapping.
        """
        lower = filename.lower()
        buf = io.BytesIO(file_bytes)

        if lower.endswith(".csv"):
            df = pl.read_csv(buf, separator=delimiter, infer_schema=False)
        elif lower.endswith((".xlsx", ".xls")):
            df = pl.read_excel(buf, infer_schema_length=0)
        else:
            raise ValueError(
                f"Unsupported file format: '{filename}'. "
                "Only .csv, .xlsx, and .xls files are supported."
            )

        return df
