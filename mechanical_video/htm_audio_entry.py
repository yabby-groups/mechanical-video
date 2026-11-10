"""Version-neutral CLI dispatch preserving frozen acoustic adapter bytes."""
import sys


def main():
    if sys.argv[1:3] == ['--engine', 'rhythm']:
        from .htm_audio_rhythm import main as rhythm_main
        return rhythm_main(sys.argv[3:])
    from .htm_audio_review import main as acoustic_main
    return acoustic_main()


if __name__ == '__main__':
    raise SystemExit(main())
