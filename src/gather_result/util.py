def find_neighbors(rates, min_value, max_value):
    try:
        min_index = rates.index(min_value)
        max_index = rates.index(max_value)

        min_before = rates[min_index - 1] if min_index > 1 else rates[min_index] # index 0 is 99999999999

        max_after = rates[max_index + 1] if max_index + 1 < len(rates) else rates[max_index]
    except:
        min_before = rates[1]
        max_after = rates[len(rates)-1]

    return min_before, max_after


def find_month_neighbors(months, min_value, max_value):
    try:
        min_index = months.index(min_value)
        max_index = months.index(max_value)

        min_before = months[min_index - 1] if min_index > 1 else months[min_index]  

        max_after = months[max_index + 1] if max_index + 1 < len(months) else months[max_index]
    except:
        min_before = months[1]
        max_after = months[len(months)-1]

    return min_before, max_after