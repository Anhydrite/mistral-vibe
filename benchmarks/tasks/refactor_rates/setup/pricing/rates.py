def tax_rate(country):
    table = {"FR": 0.20, "DE": 0.20, "ES": 0.21}
    return table.get(country.upper(), 0.0)
