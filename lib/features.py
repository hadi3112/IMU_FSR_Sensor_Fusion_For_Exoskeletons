from .derivatives import compute_derivative
from .filters import filter_derivative

def build_feature_vector(ax1, ay1, az1, ax2, ay2, az2, prev_vals):

    dx1 = filter_derivative("dx1", compute_derivative(prev_vals, "imu1_ax", ax1))
    dy1 = filter_derivative("dy1", compute_derivative(prev_vals, "imu1_ay", ay1))
    dz1 = filter_derivative("dz1", compute_derivative(prev_vals, "imu1_az", az1))

    dx2 = filter_derivative("dx2", compute_derivative(prev_vals, "imu2_ax", ax2))
    dy2 = filter_derivative("dy2", compute_derivative(prev_vals, "imu2_ay", ay2))
    dz2 = filter_derivative("dz2", compute_derivative(prev_vals, "imu2_az", az2))

    fsr_values = [0.0] * 6

    feature_vector = [
        ax1, ay1, az1,
        ax2, ay2, az2,
        dx1, dy1, dz1,
        dx2, dy2, dz2,
        *fsr_values
    ]

    return feature_vector, dx1, dy1, dz1, dx2, dy2, dz2