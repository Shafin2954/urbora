from datetime import date

from backend.schemas import SeasonPlan
from backend.tools.season_plan import season_plan

REQUIRED_CATEGORIES = {
    "land_prep", "sowing", "fertilizer", "irrigation",
    "weeding", "pest_checkpoint", "harvest",
}

ALL_CROPS = ["potato", "lentil", "mustard", "boro_rice", "aman_rice"]


def test_potato_plan_is_typed_cited_and_deterministic():
    result = season_plan("farm-1", "potato", "2026-11-01")
    plan = SeasonPlan.model_validate(result["plan"])
    assert [task.date for task in plan.tasks] == [
        "2026-10-25", "2026-11-01", "2026-11-23", "2026-11-28",
        "2026-12-03", "2026-12-11", "2026-12-13", "2027-01-02", "2027-01-30",
    ]
    assert all(task.provenance.source_type == "static_table" for task in plan.tasks)
    assert all(task.provenance.locator for task in plan.tasks)


def test_plan_rejects_unconfirmed_or_unsupported_inputs():
    assert "plan" in season_plan("farm-1", "aman_rice", "2026-07-20")
    assert "error" in season_plan("farm-1", "potato", "not-a-date")


def test_plan_is_deterministic_across_calls():
    first = season_plan("farm-1", "boro_rice", "2026-01-15")["plan"]
    second = season_plan("farm-1", "boro_rice", "2026-01-15")["plan"]
    # retrieved_at is a live timestamp; strip it before comparing determinism
    # of everything else (dates/tasks/categories/locators/formula).
    def strip(plan):
        return [
            {k: v for k, v in task.items() if k != "provenance"}
            | {k: v for k, v in task["provenance"].items() if k != "retrieved_at"}
            for task in plan["tasks"]
        ]

    assert strip(first) == strip(second)


def test_every_crop_covers_the_full_named_sequence_in_order():
    """Competition brief (Tier 0 item 4): land prep -> sowing -> fertilizer
    splits -> irrigation -> weed checkpoint -> pest checkpoint -> harvest.
    Every crop must hit all seven category types, every crop must end on a
    harvest task, and dates must be non-decreasing (chronological)."""
    for crop in ALL_CROPS:
        result = season_plan("farm-1", crop, "2026-11-01")
        plan = SeasonPlan.model_validate(result["plan"])

        categories = {task.category for task in plan.tasks}
        missing = REQUIRED_CATEGORIES - categories
        assert not missing, f"{crop} is missing categories: {missing}"

        dates = [date.fromisoformat(task.date) for task in plan.tasks]
        assert dates == sorted(dates), f"{crop} tasks are not in chronological order"

        assert plan.tasks[-1].category == "harvest", f"{crop} does not end on a harvest task"

        # land prep must precede sowing, sowing must precede harvest.
        land_prep_date = next(t.date for t in plan.tasks if t.category == "land_prep")
        sowing_date = next(t.date for t in plan.tasks if t.category == "sowing")
        harvest_date = next(t.date for t in plan.tasks if t.category == "harvest")
        assert land_prep_date <= sowing_date < harvest_date


def test_every_task_carries_provenance_with_locator_and_confidence():
    for crop in ALL_CROPS:
        result = season_plan("farm-1", crop, "2026-11-01")
        plan = SeasonPlan.model_validate(result["plan"])
        for task in plan.tasks:
            assert task.provenance.source_type == "static_table"
            assert task.provenance.locator
            assert task.provenance.confidence in {"high", "medium", "low"}


def test_pest_checkpoints_name_an_actual_pest_not_a_generic_check():
    generic_markers = ["পোকা পরীক্ষা করুন", "পরীক্ষা"]
    named_pests_bn = ["মাজরা", "জাব পোকা", "লেট ব্লাইট", "ফড়িং"]
    for crop in ALL_CROPS:
        result = season_plan("farm-1", crop, "2026-11-01")
        plan = SeasonPlan.model_validate(result["plan"])
        pest_tasks = [t for t in plan.tasks if t.category == "pest_checkpoint"]
        assert pest_tasks, f"{crop} has no pest_checkpoint task"
        for task in pest_tasks:
            assert any(name in task.task or name in task.details for name in named_pests_bn), (
                f"{crop} pest checkpoint '{task.task}' does not name a specific pest/disease"
            )
