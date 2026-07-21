from time import perf_counter


class Timing:
    def __init__(self, name=""):
        self.name = name
        self.start = perf_counter()

    def __enter__(self):
        self.start = perf_counter()

    def __exit__(self, exc_type, exc_val, exc_tb):
        now = perf_counter()
        time = (now - self.start) * 1000
        unit = "ms"
        if time < 1:
            unit = "μs"
            time *= 1000
            if time < 1:
                unit = "ns"
                time *= 1000
        if self.name == "":
            print(f"运行耗时 {time}{unit}")
        else:
            print(f"{self.name} 运行耗时 {time}{unit}")
        return False


__all__ = ["Timing"]
