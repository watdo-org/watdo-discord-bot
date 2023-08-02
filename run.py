if __name__ == "__main__":
    import sys
    from watdo import main

    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
