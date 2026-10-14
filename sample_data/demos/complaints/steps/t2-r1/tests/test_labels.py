from complaintkit.labels import parse


def test_reads_plain_answers():
    assert parse("Mortgage") == "mortgage"
    assert parse("A checking account") == "checking_savings"
    assert parse("Credit card") == "credit_card"


def test_common_product_aliases():
    assert parse("The issue concerns a home loan") == "mortgage"
    assert parse("This is a credit bureau reporting issue") == "credit_reporting"
    assert parse("debt collector") == "debt_collection"
    assert parse("bank account") == "checking_savings"
    assert parse("funds transfer") == "money_transfer"
    assert parse("credit_reporting") == "credit_reporting"


def test_ambiguous_products_are_unknown():
    assert parse("credit card and mortgage") == "unknown"
    assert parse("Debt collection / credit reporting") == "unknown"


def test_unrecognised_answers_are_unknown():
    assert parse("I am not sure") == "unknown"
