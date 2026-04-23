# fsr debug code

FSR_DEBUG = True

def debug_fsr(payload):
    if not FSR_DEBUG:
        return

    try:
        print(
            f"[FSR] "
            f"1(toe)={payload.get('fsr1')} | "
            f"2(ankle)={payload.get('fsr2')} | "
            f"3(toe)={payload.get('fsr3')}"
        )
    except Exception as e:
        print(f"[FSR DEBUG ERROR] {e}")