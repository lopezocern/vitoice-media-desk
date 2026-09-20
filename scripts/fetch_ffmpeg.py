"""下载完整版 FFmpeg（essentials 档）并提取 ffmpeg.exe / ffprobe.exe 到目标目录。

gyan.dev 与 GitHub 官方镜像均可；essentials 已含本项目所需的 libx264 / libx265 /
libvpx(WebM/VP8) / nvenc。默认优先用快速源（GitHub 官方镜像）。也可自行下载后
调用 --source <zip/7z路径> 离线安装（7z 解压需本机装有 7-Zip）。
用法：
  python scripts/fetch_ffmpeg.py [目标目录]
  python scripts/fetch_ffmpeg.py --source D:\\ffmpeg.zip <目标目录>
"""
from __future__ import annotations

import os, shutil, subprocess, sys, tempfile, urllib.request, zipfile
from pathlib import Path

GYAN_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
GH_API = "https://api.github.com/repos/GyanD/codexffmpeg/releases/latest"


def _github_essentials_url() -> str | None:
    """从 GitHub 官方镜像查询最新 essentials 压缩包下载地址。"""
    try:
        req = urllib.request.Request(GH_API, headers={"User-Agent": "mediadesk"})
        data = urllib.request.urlopen(req, timeout=20).read()
        import json
        release = json.loads(data)
        for asset in release.get("assets", []):
            name = asset.get("name", "")
            if name.endswith(("_build.zip", "_build.7z")):
                return asset["browser_download_url"]
    except Exception:
        pass
    return None


def _download(url: str, dest: Path) -> None:
    print(f"下载中: {url}")
    urllib.request.urlretrieve(url, dest)  # noqa: S310
    print(f"已下载 → {dest}")


def _run7z(zip_path: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    seven = shutil.which("7z") or r"C:\Program Files\7-Zip\7z.exe"
    cmd = [seven, "e", str(zip_path), "-o" + str(dest), "-y"]
    subprocess.run(cmd, check=True)


def _extract(zip_path: Path, dest: Path) -> None:
    if zip_path.suffix.lower() == ".7z":
        _run7z(zip_path, dest)
        _copy_members(dest, ["ffmpeg.exe", "ffprobe.exe"])
        return
    dest.mkdir(parents=True, exist_ok=True)
    wanted = {"ffmpeg.exe", "ffprobe.exe"}
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            top = name.split("/", 1)[-1]
            if top in wanted and not name.endswith("/"):
                with z.open(name) as src, (dest / top).open("wb") as out:
                    shutil.copyfileobj(src, out)
    _require(dest, wanted)


def _copy_members(dest: Path, names: list[str]) -> None:
    for n in names:
        hits = list(dest.rglob(n))
        if not hits:
            raise RuntimeError(f"归档中未找到 {n}")
        src = hits[0]
        shutil.copy2(src, dest / n)


def _require(dest: Path, names: set[str]) -> None:
    for fn in names:
        if not (dest / fn).exists():
            raise RuntimeError(f"随包缺失 {fn}")


def fetch_ffmpeg(dest: Path, source: str | None = None, fast: bool = True) -> None:
    if source and Path(source).exists():
        _extract(Path(source), dest)
        print(f"已从本地 {source} 提取 ffmpeg/ffprobe → {dest}")
        return
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / ("ffmpeg.7z" if fast else "ffmpeg.zip")
        tried = []
        url = _github_essentials_url() if fast else None
        if url:
            tried.append("GitHub镜像")
            _download(url, tmp)
        else:
            tried.append("gyan.dev")
            _download(os.environ.get("FFMPEG_URL", GYAN_URL), tmp)
        _extract(tmp, dest)
    print(f"完成（{'+'.join(tried)}）：ffmpeg/ffprobe → {dest}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    src = None
    if "--source" in sys.argv:
        i = sys.argv.index("--source")
        src = sys.argv[i + 1]
    target = Path(args[0]) if args else Path("dist/MediaDesk/ffmpeg/bin")
    fetch_ffmpeg(target, src)