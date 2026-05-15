"""Command-line interface for spotmap."""

import argparse
import sys


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="spotmap",
        description="Generate an interactive epidemiological spot map for India.",
    )
    p.add_argument("csv", help="Path to the input CSV file with point data.")
    p.add_argument(
        "-o", "--output",
        default="spotmap_output.html",
        help="Output HTML file path (default: spotmap_output.html).",
    )
    p.add_argument("--state-shp", default=None, help="Custom state boundary file.")
    p.add_argument("--district-shp", default=None, help="Custom district boundary file.")
    p.add_argument("--lat-col", default=None, help="Latitude column name.")
    p.add_argument("--lon-col", default=None, help="Longitude column name.")
    p.add_argument("--outcome-col", default=None, help="Outcome column name.")
    p.add_argument("--case-value", default=None, help="Value that represents a case.")
    p.add_argument(
        "--count-cutoff",
        type=int,
        default=2,
        help="District count threshold for mode selection (default: 2).",
    )
    p.add_argument(
        "--cluster-color",
        default="#E85252",
        help="Hex colour for dot-density clusters (default: #E85252).",
    )
    p.add_argument(
        "--case-color",
        default="#D55757",
        help="Hex colour for case pins (default: #D55757).",
    )
    p.add_argument(
        "--control-color",
        default="#7676E7",
        help="Hex colour for control pins (default: #7676E7).",
    )
    return p


def main(argv=None) -> None:
    from .map_builder import SpotMap

    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        SpotMap(
            args.csv,
            state_shp=args.state_shp,
            district_shp=args.district_shp,
            lat_col=args.lat_col,
            lon_col=args.lon_col,
            outcome_col=args.outcome_col,
            case_value=args.case_value,
            count_cutoff=args.count_cutoff,
            cluster_color=args.cluster_color,
            case_color=args.case_color,
            control_color=args.control_color,
        ).build().save(args.output)
        print(f"Map saved to: {args.output}")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
