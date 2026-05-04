import argparse
import io
import time
import zipfile
from pathlib import Path
from typing import Dict, List

import requests


class TWICDownloader:
    def __init__(
        self,
        download_dir: str = "twic/data/twic_zips",
        extract_dir: str = "twic/data/pgns",
    ):
        self.download_dir: Path = Path(download_dir)
        self.extract_dir: Path = Path(extract_dir)
        self.base_url: str = "https://theweekinchess.com/zips/twic{number}g.zip"
        self.failed_issues: List[int] = []

        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.extract_dir.mkdir(parents=True, exist_ok=True)

        self.headers: Dict[str, str] = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    def download_range(self, start: int, end: int) -> None:
        """
        Downloads a range of TWIC issues and extracts PGNs.
        """
        for issue_num in range(start, end + 1):
            self._process_issue_with_retry(issue_num)
            time.sleep(1)

        if self.failed_issues:
            print(f"\nFailed issues: {self.failed_issues}")

    def _process_issue_with_retry(
        self,
        issue_num: int,
        max_retries: int = 3,
    ) -> None:
        url = self.base_url.format(number=issue_num)
        zip_path = self.download_dir / f"twic{issue_num}.zip"

        # Avoid re-downloading existing zips.
        if zip_path.exists():
            print(f"Issue {issue_num}: zip already exists, extracting again.")
            try:
                with zipfile.ZipFile(zip_path, "r") as z:
                    z.extractall(self.extract_dir)
                return
            except Exception as exc:
                print(f"  -> Existing zip could not be extracted: {exc}")

        for attempt in range(1, max_retries + 1):
            try:
                print(f"Fetching issue {issue_num} ({attempt}/{max_retries})...")
                response = requests.get(
                    url,
                    headers=self.headers,
                    timeout=20,
                )

                if response.status_code == 200:
                    with open(zip_path, "wb") as f:
                        f.write(response.content)

                    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                        z.extractall(self.extract_dir)

                    print(f"  -> Successfully processed issue {issue_num}")
                    return

                print(f"  -> Server returned status {response.status_code}")

            except requests.exceptions.ReadTimeout:
                print("  -> Read timed out.")
            except Exception as exc:
                print(f"  -> Error: {exc}")

            if attempt < max_retries:
                sleep_time = attempt * 3
                print(f"  -> Waiting {sleep_time}s before retrying...")
                time.sleep(sleep_time)

        print(f"  -> FAILED issue {issue_num}")
        self.failed_issues.append(issue_num)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    args = parser.parse_args()

    downloader = TWICDownloader()
    downloader.download_range(args.start, args.end)


if __name__ == "__main__":
    main()