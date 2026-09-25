import gzip
import os
from pathlib import Path
import random
import subprocess

import modal

from cs336_data.modal_utils import VOLUME_MOUNTS, app, build_image, data_volume

REMOTE_DATA_DIR = Path("/root/data")
REMOTE_URLS_FILE = REMOTE_DATA_DIR / "subsampled_positive_urls.txt"
REMOTE_WARC_PREFIX = REMOTE_DATA_DIR / "subsampled_positive_urls.warc"
WIKI_URLS_GZ = Path("/shared-data/wiki/enwiki-20260501-extracted_urls.txt.gz")

BATCH_SIZE = 1000
NUM_BATCHES = 5


def sample_urls_from_wiki(gz_path: Path, num_samples: int = 10000) -> list[str]:
    """Sample valid URLs using reservoir sampling to keep memory footprint minimal."""
    print(f"[Sampling] Sampling {num_samples} URLs from {gz_path}...", flush=True)
    sampled: list[str] = []
    with gzip.open(gz_path, "rt", encoding="utf-8", errors="ignore") as f:
        for idx, line in enumerate(f):
            url = line.strip()
            if not url or not (url.startswith("http://") or url.startswith("https://")):
                continue
            if len(sampled) < num_samples:
                sampled.append(url)
            else:
                r = random.randint(0, idx)
                if r < num_samples:
                    sampled[r] = url
    print(f"[Sampling] Sampling complete. Extracted {len(sampled)} URLs.", flush=True)
    return sampled


@app.function(image=build_image(), volumes=VOLUME_MOUNTS, timeout=60 * 60 * 2)
def crawl_positive_urls_batch(urls_content: str, batch_index: int):
    """Crawl a single batch of URLs and save to a batch-specific WARC file."""
    REMOTE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 写入本批次的 URL 文件
    batch_urls_file = REMOTE_DATA_DIR / f"batch_{batch_index}_urls.txt"
    warc_prefix = REMOTE_DATA_DIR / f"batch_{batch_index}"

    url_list = [u for u in urls_content.splitlines() if u.strip()]
    print(f"[Batch {batch_index}] Writing {len(url_list)} URLs to {batch_urls_file}...", flush=True)
    with open(batch_urls_file, "w", encoding="utf-8") as f:
        f.write("\n".join(url_list) + "\n")

    # 2. 调用 wget 抓取为 WARC
    cmd = [
        "wget",
        "--timeout=5",
        "-t", "1",
        "-i", str(batch_urls_file),
        f"--warc-file={warc_prefix}",
        "-O", "/dev/null",
    ]
    print(f"[Batch {batch_index}] Starting wget: {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, capture_output=False)
    print(f"[Batch {batch_index}] wget finished with exit code: {result.returncode}", flush=True)

    # 3. 检查生成的 WARC 文件
    warc_files = list(REMOTE_DATA_DIR.glob(f"batch_{batch_index}*.warc*"))
    if warc_files:
        for warc_file in sorted(warc_files):
            size_mb = warc_file.stat().st_size / (1024 * 1024)
            print(f"[Batch {batch_index}] WARC: {warc_file.name} ({size_mb:.2f} MB)", flush=True)
    else:
        print(f"[Batch {batch_index}] Warning: No WARC file found!", flush=True)

    # 4. 持久化 Volume 刷盘
    print(f"[Batch {batch_index}] Committing volume...", flush=True)
    data_volume.commit()
    print(f"[Batch {batch_index}] Done.", flush=True)


@app.local_entrypoint()
def main():
    local_urls_file = Path("data/subsampled_positive_urls.txt")

    if not local_urls_file.exists():
        print(f"[Local] ERROR: {local_urls_file} not found!", flush=True)
        return

    with open(local_urls_file, "r", encoding="utf-8") as f:
        all_urls = [line.strip() for line in f if line.strip()]

    # 取前 NUM_BATCHES * BATCH_SIZE 个 URL，切分为 NUM_BATCHES 批
    target_urls = all_urls[: NUM_BATCHES * BATCH_SIZE]
    batches = [
        target_urls[i : i + BATCH_SIZE]
        for i in range(0, len(target_urls), BATCH_SIZE)
    ]

    batch_contents = ["\n".join(batch) for batch in batches]
    batch_indices = list(range(len(batches)))

    print(
        f"[Local] Submitting {len(batches)} batches of {BATCH_SIZE} URLs each in parallel...",
        flush=True,
    )

    # for_each 并行提交所有批次，等待全部完成后返回
    crawl_positive_urls_batch.for_each(batch_contents, batch_indices)

    print("[Local] All batches completed!", flush=True)
