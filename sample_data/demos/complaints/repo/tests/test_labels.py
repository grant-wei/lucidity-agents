from complaintkit.labels import parse


def test_reads_plain_answers():
    assert parse("Mortgage") == "mortgage"
    assert parse("A checking account") == "checking_savings"
    assert parse("Credit card") == "credit_card"


def test_unrecognised_answers_are_unknown():
    assert parse("I am not sure") == "unknown"
