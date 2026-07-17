import asyncio

async def quick(tag):
    print(f"Q{tag}")
    return tag

async def slow(tag):
    print(f"S{tag}-in")
    await asyncio.sleep(0)
    print(f"S{tag}-out")
    return tag

async def main():
    t1 = asyncio.create_task(slow(1))
    t1.add_done_callback(lambda _: print("CB1"))
    t2 = asyncio.create_task(slow(2))
    t2.cancel()
    print("M1")
    await quick(3)
    print("M2")
    await asyncio.sleep(0)
    print("M3")
    try:
        await t2
    except asyncio.CancelledError:
        print("C2")
    print("M4", t1.done())
    await t1
    print("M5")

asyncio.run(main())
