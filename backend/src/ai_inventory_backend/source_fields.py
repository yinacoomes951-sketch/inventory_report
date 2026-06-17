SOURCE_TABLE = "lx_ads.ads_lx_kd_inventory_sku_calc"

SOURCE_FIELD_MAP = {
    "sku": "sku",
    "product_name": "产品名称",
    "owner": "归属",
    "spu": "spu",
    "department_name": "部门名称",
    "category": "类目",
    "region": "区域",
    "recent_daily_sales": "近期日销",
    "total_inventory": "总库存",
    "sellable_days": "可售天数",
    "suggested_sellable_days": "建议可售天数",
    "forecast_daily_sales": "预测日销",
    "suggested_restock_qty": "建议备货量",
    "restock_warning": "备货预警",
    "purchase_in_transit": "采购在途",
    "domestic_total_qty": "国内总数量",
    "fba_available": "fba可售",
    "awd_available": "awd可用",
    "overseas_ready_qty": "国外合计",
    "sales_7d": "最近7天总销量",
    "sales_15d": "最近15天总销量",
    "sales_21d": "最近21天总销量",
    "sales_30d": "最近30天总销量",
    "insert_time": "insert_time",
}

REQUIRED_SOURCE_FIELDS = tuple(SOURCE_FIELD_MAP.values())


def source_column(internal_name: str) -> str:
    return SOURCE_FIELD_MAP[internal_name]
