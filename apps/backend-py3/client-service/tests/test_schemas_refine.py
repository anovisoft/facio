"""Refine request accepts batch answers + comment (and legacy single answer)."""

from app.schemas.api import RefineProjectRequest


def test_batch_answers_and_comment():
    body = RefineProjectRequest.model_validate(
        {
            "answers": [
                {"question_id": "q_servings", "value": "2"},
                {"question_id": "q_meat", "value": "гуанчиале"},
            ],
            "comment": "без чеснока",
        }
    )
    assert len(body.answers) == 2
    assert body.comment == "без чеснока"


def test_comment_only_ok():
    body = RefineProjectRequest.model_validate({"comment": "ещё важно"})
    assert body.answers == []
    assert body.comment == "ещё важно"


def test_legacy_answer_normalized():
    body = RefineProjectRequest.model_validate(
        {"answer": "2", "question_id": "q_servings"}
    )
    assert len(body.answers) == 1
    assert body.answers[0].question_id == "q_servings"
    assert body.answers[0].value == "2"


def test_empty_payload_ok_for_skip():
    """Create Plan Feed skip CTA may refine with no answers/comment."""
    body = RefineProjectRequest.model_validate({})
    assert body.answers == []
    assert body.comment is None


def test_blank_comment_alone_normalizes_to_empty():
    body = RefineProjectRequest.model_validate({"comment": "   "})
    assert body.answers == []
    assert body.comment is None
