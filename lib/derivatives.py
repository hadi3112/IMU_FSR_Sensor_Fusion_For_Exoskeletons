def compute_derivative(prev_dict, key, current_value):
    prev = prev_dict[key]
    if prev is None:
        prev_dict[key] = current_value
        return 0.0

    derivative = current_value - prev
    prev_dict[key] = current_value
    return derivative