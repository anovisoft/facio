from facio_domain.pain import reports_pain


def test_lower_back_taking_load_is_pain() -> None:
    assert reports_pain("поясница забирает нагрузку")


def test_hurts_and_injury_are_pain() -> None:
    assert reports_pain("больно, давай 40")
    assert reports_pain("it hurts")
    assert reports_pain("травма в плече")


def test_plain_target_is_not_pain() -> None:
    assert not reports_pain("цель 30")
    assert not reports_pain("давай три раза в неделю")
