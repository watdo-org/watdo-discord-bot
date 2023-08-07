if __name__ == "__main__":
    import os
    import sys
    from watdo import main
    from watdo.environ import IS_DEV

    if IS_DEV and os.name != "nt":
        import time

        os.environ["TZ"] = "Europe/London"
        time.tzset()

    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
