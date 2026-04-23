FILTER_DERIVATIVES = True
DERIV_ALPHA = 0.2

prev_deriv = {
    "dx1": 0.0, "dy1": 0.0, "dz1": 0.0,
    "dx2": 0.0, "dy2": 0.0, "dz2": 0.0,
}

def low_pass_filter(prev, new, alpha=0.2):
    return alpha * new + (1 - alpha) * prev

def filter_derivative(key, raw_value):
    if not FILTER_DERIVATIVES:
        return raw_value

    smoothed = low_pass_filter(prev_deriv[key], raw_value, DERIV_ALPHA)
    prev_deriv[key] = smoothed
    return smoothed