from moderation.scoring import build_result


def test_peak_category_becomes_score():
    class Item:
        flagged = True
        category_scores = {"harassment": 0.91, "violence": 0.20}

    class Response:
        results = [Item()]

    result = build_result(Response())
    assert result.score == 9.1
    assert result.flagged is True
    assert result.test_emoji == "🔴"


def test_low_score_is_green():
    class Item:
        flagged = False
        category_scores = {"harassment": 0.12, "violence": 0.03}

    class Response:
        results = [Item()]

    result = build_result(Response())
    assert result.score == 1.2
    assert result.test_emoji == "🟢"
