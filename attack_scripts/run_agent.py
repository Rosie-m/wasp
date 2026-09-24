import argparse
import subprocess
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Run the agent script for a given config directory")
    parser.add_argument("--config-dir", type=str, required=True, help="Path to the config directory containing run_agent.sh")
    return parser.parse_args()


def main():
    args = parse_args()
    config_dir = Path(args.config_dir)
    run_agent_sh = config_dir / "run_agent.sh"

    if not run_agent_sh.exists():
        raise FileNotFoundError(f"run_agent.sh not found in {config_dir}")

    subprocess.run(["bash", str(run_agent_sh)], check=True)


if __name__ == "__main__":
    main()
