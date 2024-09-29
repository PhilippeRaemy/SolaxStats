import re


def test_re():
    for period in ('2024', '2024-09', '2024-09-25', '2024-09-25..2024-09-30'):
        ma = re.match('(?P<from>(\d{4}((-(?P<mm>\d\d))?(-(?P<dd>\d\d))?)?))(..(?P<to>\d{4}-\d\d-\d\d))?$', period)
        print(period, ma.groupdict() if ma else 'not match')
