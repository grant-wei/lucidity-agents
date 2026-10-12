from scaler.units import to_metric


def test_cup():
    assert to_metric(1, 'cup') == (236.6, 'ml')


def test_oz():
    assert to_metric(2, 'oz') == (56.7, 'g')
