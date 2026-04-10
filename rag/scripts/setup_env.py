import subprocess
import sys

TEMPLATE_PATH = ".env.example"
ENV_FILE_PATH = ".env"


def get_secrets():
    """
    Resolves 1password secret references and populates .env file.
    """
    try:
        print("Resolving secrets...")
        logs = subprocess.run(
            ["op", "inject", "-i", TEMPLATE_PATH, "-o", ENV_FILE_PATH],
            capture_output=True,
            text=True,
        )
        if logs.returncode != 0:
            raise Exception(logs.stderr)

        print("Secrets loaded!")
    except Exception as e:
        print(f"Unable to load secrets! Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    get_secrets()
