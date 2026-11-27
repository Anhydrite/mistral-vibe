def invoice_total(lines, country):
    rate = {"FR": 0.20, "DE": 0.20, "ES": 0.21}.get(country.upper(), 0.0)
    return round(sum(price * qty for price, qty in lines) * (1 + rate))
