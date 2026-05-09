from race_engine.backtest.ablations import ablation_configs, engine_contributions


def test_each_major_engine_can_be_turned_off_for_paired_comparison() -> None:
    configs = ablation_configs()

    assert configs[0].name == "baseline_static_allocation"
    assert configs[-1].signal_efficacy is True
    assert any(config.trade_quality is False for config in configs)
    assert len(configs) == 9


def test_engine_contribution_table_is_incremental() -> None:
    sharpes = {config.name: float(index) for index, config in enumerate(ablation_configs())}

    contributions = engine_contributions(sharpes)

    assert all(value == 1.0 for value in contributions.values())

