"""
Sales Generator - Create customer-facing proposals, demos, and business cases
"""

from .sales_db import SalesGeneratorDatabase
from .sales_manager import SalesGeneratorManager

__all__ = ["SalesGeneratorDatabase", "SalesGeneratorManager"]
