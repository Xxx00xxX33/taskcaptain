#!/usr/bin/env python3
from __future__ import annotations

try:
    from tc_page_index import render_index_page
    from tc_page_product import render_product_page
except ModuleNotFoundError:
    from app.tc_page_index import render_index_page
    from app.tc_page_product import render_product_page


__all__ = ['render_index_page', 'render_product_page']
