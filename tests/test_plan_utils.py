from plan_utils import is_unlimited_usage, plan_display_name, show_upgrade_nudge


def test_show_upgrade_nudge_hides_top_tiers():
    assert show_upgrade_nudge("professional") is False
    assert show_upgrade_nudge("team") is False
    assert show_upgrade_nudge("unlimited") is False
    assert show_upgrade_nudge("starter") is True
    assert show_upgrade_nudge("none") is True


def test_plan_display_name():
    assert plan_display_name("unlimited") == "Unlimited"
    assert plan_display_name(None) == "Free"


def test_is_unlimited_usage():
    assert is_unlimited_usage("unlimited", 999999) is True
    assert is_unlimited_usage("starter", 10) is False
    assert is_unlimited_usage("none", 999999) is True
