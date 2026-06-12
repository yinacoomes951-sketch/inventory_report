from ai_inventory_backend.diagnosis import RoleScope
from ai_inventory_backend.repository import InventoryRepository, _report_inventory_cte


class _Result:
    def __init__(self, row=None):
        self.row = row or {}

    def mappings(self):
        return self

    def one(self):
        return self.row

    def all(self):
        return []


class _Connection:
    def __init__(self, statements, row):
        self.statements = statements
        self.row = row

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, statement, params):
        self.statements.append(str(statement))
        return _Result(self.row)


class _Engine:
    def __init__(self, row=None):
        self.statements = []
        self.row = row

    def connect(self):
        return _Connection(self.statements, self.row)


def _scope(where_sql="", params=None):
    return RoleScope(
        id="test-scope",
        level="运营个人",
        object_name="测试对象",
        where_sql=where_sql,
        params=params or {},
    )


def test_report_inventory_cte_filters_after_role_scope_and_spu_aggregation():
    sql = _report_inventory_cte(_scope('and "归属" = :owner', {"owner": "张三"}))

    assert 'and "归属" = :owner' in sql
    assert 'sum(coalesce("总库存", 0)) over (partition by spu)' in sql
    assert 'sum(coalesce("预测日销", 0)) over (partition by spu)' in sql
    assert "report_spu_total_inventory <> 0 or report_spu_demand_daily <> 0" in sql


def test_all_report_queries_use_the_same_reportable_spu_scope():
    engine = _Engine()
    repository = object.__new__(InventoryRepository)
    repository.engine = engine
    batch = {"insert_time": "2026-06-12"}
    scope = _scope('and "部门名称" = :department', {"department": "测试部门"})

    repository._scope_metrics(batch, scope)
    repository._spu_health(batch, scope)
    repository._warning_distribution(batch, scope)
    repository._top_risk_skus(batch, scope)

    assert len(engine.statements) == 4
    for sql in engine.statements:
        assert "report_inventory as" in sql
        assert "report_spu_total_inventory <> 0 or report_spu_demand_daily <> 0" in sql
        assert 'and "部门名称" = :department' in sql


def test_zero_inventory_or_zero_forecast_alone_does_not_exclude_spu():
    sql = _report_inventory_cte(_scope())

    assert "report_spu_total_inventory <> 0 or report_spu_demand_daily <> 0" in sql
    assert "report_spu_total_inventory <> 0 and report_spu_demand_daily <> 0" not in sql


def test_top_dimension_excludes_double_zero_spu_after_dimension_aggregation():
    engine = _Engine({"name": "张三"})
    repository = object.__new__(InventoryRepository)
    repository.engine = engine

    assert repository._top_dimension({"insert_time": "2026-06-12"}, "归属") == "张三"

    sql = engine.statements[0]
    assert 'coalesce("归属", \'未归属\') as name' in sql
    assert "group by 1, spu" in sql
    assert "where total_inventory <> 0 or demand_daily <> 0" in sql
