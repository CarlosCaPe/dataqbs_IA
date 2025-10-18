from concurrent.futures import ProcessPoolExecutor


def task(x):
    return [1, 2, 3, x]


def run():
    with ProcessPoolExecutor(max_workers=1) as p:
        f = p.submit(task, 42)
        r = f.result()
        print(type(r), r)


if __name__ == '__main__':
    run()
