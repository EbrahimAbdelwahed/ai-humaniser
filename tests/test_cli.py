from academic_engine.cli import build_parser


def test_cli_accepts_calibrate_flash_detector_set():
    parser = build_parser()

    args = parser.parse_args(
        [
            "calibrate",
            "examples/input/political_science.txt",
            "-o",
            "out.json",
            "--mock-provider",
            "--detectors",
            "local+flash",
        ]
    )

    assert args.command == "calibrate"
    assert args.detectors == "local+flash"
    assert args.flash_mode == "calibration"


def test_cli_accepts_raw_audit_inputs():
    parser = build_parser()

    args = parser.parse_args(
        [
            "raw-audit",
            "a.txt",
            "b.txt",
            "-o",
            "out.json",
            "--detectors",
            "local+flash",
        ]
    )

    assert args.command == "raw-audit"
    assert [str(path) for path in args.inputs] == ["a.txt", "b.txt"]
    assert args.detectors == "local+flash"
    assert args.flash_mode == "calibration"


def test_cli_accepts_official_detector_sets():
    parser = build_parser()

    raw_args = parser.parse_args(
        [
            "raw-audit",
            "a.txt",
            "-o",
            "out.json",
            "--detectors",
            "local+official",
        ]
    )
    health_args = parser.parse_args(["detector-health", "--detectors", "official"])

    assert raw_args.detectors == "local+official"
    assert health_args.detectors == "official"
