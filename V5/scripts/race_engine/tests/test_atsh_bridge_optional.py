from add_trim_sell_hold import main as atsh_main


def test_atsh_bridge_existing_behavior_unchanged_without_flag(capsys) -> None:
    assert atsh_main([]) == 0
    assert "RACE engine disabled" in capsys.readouterr().out

