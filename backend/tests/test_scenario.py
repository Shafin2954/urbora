from backend.tools.scenario import simulate_budget


def test_budget_scenario_recomputes_server_side():
    result = simulate_budget("Rajshahi", "clay_loam", "irrigated", "rabi", 1, "bigha", 20000, -40)
    assert result["scenario_budget_bdt"] == 12000
    assert result["formula"]
    assert result["scenario_ranking"]["candidates"]
