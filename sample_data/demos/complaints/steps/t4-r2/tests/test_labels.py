from complaintkit.labels import parse


def test_reads_plain_answers():
    assert parse("Mortgage") == "mortgage"
    assert parse("A checking account") == "checking_savings"
    assert parse("Credit card") == "credit_card"


def test_recognizes_common_synonyms_and_explicit_primary_product():
    assert parse("The issue concerns a Zelle transfer") == "money_transfer"
    assert parse("The primary product is debt collection, not the credit report") == "debt_collection"
    assert parse("An attempt to collect a past-due debt") == "debt_collection"


def test_unrecognised_answers_are_unknown():
    assert parse("I am not sure") == "unknown"
