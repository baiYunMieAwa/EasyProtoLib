from time import perf_counter


class Timing:
    def __init__(self, name=""):
        self.name = name
        self.last = self.start = perf_counter()

    def add_part(self, name=""):
        now = perf_counter()
        time = (now - self.last) * 1000
        self.last = now
        unit = "ms"
        if time < 1:
            unit = "μs"
            time *= 1000
            if time < 1:
                unit = "ns"
                time *= 1000
        if name == "":
            print(f"运行耗时 {time:.4}{unit}")
        else:
            print(f"{name} 运行耗时 {time:.4}{unit}")

    def __enter__(self):
        self.start = self.last = perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        now = perf_counter()
        time = (now - self.start) * 1000
        self.start = now
        unit = "ms"
        if time < 1:
            unit = "μs"
            time *= 1000
            if time < 1:
                unit = "ns"
                time *= 1000
        if self.name == "":
            print(f"运行总耗时 {time:.4}{unit}")
        else:
            print(f"{self.name} 运行总耗时 {time:.4}{unit}")
        return False


def next_part():
    print("\n---\n")


__all__ = ["Timing", "next_part"]
