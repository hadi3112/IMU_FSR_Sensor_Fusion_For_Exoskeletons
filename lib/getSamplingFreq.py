import numpy as np

def estimate_fs(t):
    """
    Estimate sampling frequency and basic signal stats.

    Parameters:
        t (np.array): time stamps in seconds

    Returns:
        fs (float): estimated sampling frequency (Hz)
        n_samples (int): number of samples
        duration (float): total duration (seconds)
        dt_stats (dict): min/mean/max dt
    """

    t = np.array(t).flatten()

    n_samples = len(t)
    duration = t[-1] - t[0] if n_samples > 1 else 0

    dt = np.diff(t)
    dt = dt[dt > 0]  # remove invalid values

    if len(dt) == 0:
        return None, n_samples, duration, None

    fs = 1.0 / np.mean(dt)

    dt_stats = {
        "min_dt": np.min(dt),
        "mean_dt": np.mean(dt),
        "max_dt": np.max(dt)
    }

    return fs, n_samples, duration, dt_stats