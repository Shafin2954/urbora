from backend.schemas import SeasonPlan
from backend.tools.season_plan import season_plan


def test_potato_plan_is_typed_cited_and_deterministic():
    result = season_plan("farm-1", "potato", "2026-11-01")
    plan = SeasonPlan.model_validate(result["plan"])
    assert [task.date for task in plan.tasks] == [
        "2026-11-01", "2026-11-23", "2026-12-03", "2026-12-13", "2027-01-02"
    ]
    assert all(task.provenance.source_type == "static_table" for task in plan.tasks)
    assert all(task.provenance.locator for task in plan.tasks)


def test_plan_rejects_unconfirmed_or_unsupported_inputs():
    assert "plan" in season_plan("farm-1", "aman_rice", "2026-07-20")
    assert "error" in season_plan("farm-1", "potato", "not-a-date")
