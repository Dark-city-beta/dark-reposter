import asyncio

from .telegram_app import run


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
