if __name__ == "__main__":
    import sys
    from watdo import main
    from watdo.environ import IS_DEV

    if IS_DEV:
        import os
        import time

        os.environ["TZ"] = "Europe/London"
        time.tzset()

    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
