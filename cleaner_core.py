import os
import shutil
import ctypes
from ctypes import wintypes
from typing import Callable, Dict, List, Optional, Tuple

class SHQUERYRBINFO(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.DWORD),
        ('i64Size', ctypes.c_int64),
        ('i64NumItems', ctypes.c_int64)
    ]

# Whitelist validation: directories that MUST NEVER be deleted
FORBIDDEN_PATHS = [
    os.path.abspath(r"C:\Windows"),
    os.path.abspath(r"C:\Windows\System32"),
    os.path.abspath(r"C:\Program Files"),
    os.path.abspath(r"C:\Program Files (x86)"),
    os.path.abspath(r"C:\Users"),
    os.path.abspath(os.path.expanduser("~")),
    os.path.abspath(os.path.expanduser(r"~\Desktop")),
    os.path.abspath(os.path.expanduser(r"~\Documents")),
    os.path.abspath(os.path.expanduser(r"~\Downloads")),
    os.path.abspath(os.path.expanduser(r"~\Pictures")),
    os.path.abspath(os.path.expanduser(r"~\Videos")),
    os.path.abspath(os.path.expanduser(r"~\Music")),
]

def format_bytes(b: int) -> str:
    """Format bytes into readable string (B, KB, MB, GB)."""
    if b < 1024:
        return f"{b} B"
    elif b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    elif b < 1024 * 1024 * 1024:
        return f"{b / (1024 * 1024):.1f} MB"
    else:
        return f"{b / (1024 * 1024 * 1024):.2f} GB"

def get_disk_info(drive: str = "C:\\") -> Tuple[int, int, int]:
    """Returns (total_bytes, used_bytes, free_bytes) for drive."""
    total, used, free = shutil.disk_usage(drive)
    return total, used, free

def is_path_safe_to_clean(path: str) -> bool:
    """Verifies path is not a critical system/user root."""
    try:
        norm = os.path.abspath(path)
        for forbidden in FORBIDDEN_PATHS:
            if norm == forbidden or norm.startswith(forbidden + "\\") and forbidden == os.path.abspath(os.path.expanduser(r"~\Desktop")):
                # Desktop subfiles are protected
                return False
            if norm == os.path.splitdrive(norm)[0] + "\\":
                # Root drive (e.g. C:\)
                return False
        return True
    except Exception:
        return False

def get_recycle_bin_info() -> Tuple[int, int]:
    """Returns (total_bytes, item_count) in Recycle Bin."""
    try:
        rb = SHQUERYRBINFO()
        rb.cbSize = ctypes.sizeof(SHQUERYRBINFO)
        res = ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(rb))
        if res == 0:
            return rb.i64Size, rb.i64NumItems
    except Exception:
        pass
    return 0, 0

def empty_recycle_bin() -> int:
    """Empties Recycle Bin silently. Returns freed bytes."""
    size_before, _ = get_recycle_bin_info()
    try:
        # SHERB_NOCONFIRMATION (0x1) | SHERB_NOPROGRESSUI (0x2) | SHERB_NOSOUND (0x4) = 7
        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
    except Exception:
        pass
    return size_before

# Category definitions
CLEANUP_CATEGORIES = [
    {
        "id": "nv_dxcache",
        "name": "NVIDIA DirectX 셰이더 캐시",
        "desc": "게임 및 그래픽 작업 시 누적된 셰이더 캐시 (필요 시 자동 재배포, 100% 안전)",
        "paths": [os.path.expandvars(r"%LOCALAPPDATA%\NVIDIA\DXCache")],
        "recommended": True,
        "is_special": None
    },
    {
        "id": "nv_updates",
        "name": "NVIDIA App 업데이트 잔여 패키지",
        "desc": "NVIDIA 앱 자동 업데이트 후 남아있는 대용량 설치 압축본 (ota-artifacts)",
        "paths": [r"C:\ProgramData\NVIDIA Corporation\NVIDIA app\UpdateFramework\ota-artifacts"],
        "recommended": True,
        "is_special": None
    },
    {
        "id": "nv_downloader",
        "name": "NVIDIA 드라이버 다운로더 패키지",
        "desc": "과거에 다운로드된 그래픽 드라이버 설치 실행 파일 (Downloader)",
        "paths": [r"C:\ProgramData\NVIDIA Corporation\Downloader"],
        "recommended": True,
        "is_special": "nv_downloader"  # preserve 'latest' folder
    },
    {
        "id": "d3d_cache",
        "name": "DirectX 3D 디스플레이 캐시",
        "desc": "Windows D3DS 디스플레이 컴파일 캐시",
        "paths": [os.path.expandvars(r"%LOCALAPPDATA%\D3DSCache")],
        "recommended": True,
        "is_special": None
    },
    {
        "id": "user_temp",
        "name": "Windows 사용자 임시 파일 (Temp)",
        "desc": "앱 및 시스템 백그라운드가 생성한 임시 파일 (현재 사용 중인 파일은 안전하게 자동 제외)",
        "paths": [os.path.expandvars(r"%LOCALAPPDATA%\Temp")],
        "recommended": True,
        "is_special": None
    },
    {
        "id": "crash_dumps",
        "name": "시스템 오류 크래시 덤프",
        "desc": "프로그램 비정상 종료 시 기록된 오류 메모리 덤프 파일",
        "paths": [os.path.expandvars(r"%LOCALAPPDATA%\CrashDumps")],
        "recommended": True,
        "is_special": None
    },
    {
        "id": "dev_cache",
        "name": "개발 패키지 캐시 (NPM / Pip)",
        "desc": "Node.js npm 및 Python pip 패키지 다운로드 임시 캐시",
        "paths": [
            os.path.expandvars(r"%LOCALAPPDATA%\npm-cache"),
            os.path.expandvars(r"%LOCALAPPDATA%\pip\cache")
        ],
        "recommended": True,
        "is_special": None
    },
    {
        "id": "recycle_bin",
        "name": "Windows 휴지통",
        "desc": "휴지통에 들어있는 삭제 파일 영구 비우기",
        "paths": [],
        "recommended": True,
        "is_special": "recycle_bin"
    },
    {
        "id": "browser_cache",
        "name": "웹 브라우저 임시 캐시 (Chrome / Edge / Whale)",
        "desc": "웹서핑 이미지/미디어 캐시 (로그인 세션, 비밀번호, 북마크는 안전하게 보존)",
        "paths": [
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache"),
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cache"),
            os.path.expandvars(r"%LOCALAPPDATA%\Naver\Naver Whale\User Data\Default\Cache")
        ],
        "recommended": False,
        "is_special": None
    }
]

def scan_category(cat: Dict) -> Tuple[int, int]:
    """Scans category and returns (total_bytes, file_count)."""
    if cat.get("is_special") == "recycle_bin":
        return get_recycle_bin_info()

    total_bytes = 0
    file_count = 0

    for base_path in cat.get("paths", []):
        if not os.path.exists(base_path) or not is_path_safe_to_clean(base_path):
            continue

        is_downloader = (cat.get("is_special") == "nv_downloader")

        try:
            for root, dirs, files in os.walk(base_path):
                # If downloader, skip the 'latest' folder
                if is_downloader and os.path.basename(root).lower() == "latest":
                    dirs.clear()
                    continue

                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        sz = os.path.getsize(fp)
                        total_bytes += sz
                        file_count += 1
                    except Exception:
                        pass
        except Exception:
            pass

    return total_bytes, file_count

def clean_category(cat: Dict, log_cb: Optional[Callable[[str], None]] = None) -> Tuple[int, int, int]:
    """
    Cleans category files safely.
    Returns (freed_bytes, deleted_count, skipped_count).
    """
    if log_cb:
        log_cb(f"[{cat['name']}] 정리 시작...")

    if cat.get("is_special") == "recycle_bin":
        bytes_before, items_count = get_recycle_bin_info()
        empty_recycle_bin()
        if log_cb:
            log_cb(f"  → 휴지통 비우기 완료: {format_bytes(bytes_before)} 확보 ({items_count}개 항목)")
        return bytes_before, items_count, 0

    freed_bytes = 0
    deleted_count = 0
    skipped_count = 0
    is_downloader = (cat.get("is_special") == "nv_downloader")

    for base_path in cat.get("paths", []):
        if not os.path.exists(base_path) or not is_path_safe_to_clean(base_path):
            continue

        # Collect files first to avoid iterator modification issues
        file_list = []
        dir_list = []
        try:
            for root, dirs, files in os.walk(base_path, topdown=False):
                if is_downloader and "latest" in root.lower().split(os.sep):
                    continue
                for f in files:
                    file_list.append(os.path.join(root, f))
                for d in dirs:
                    if is_downloader and d.lower() == "latest":
                        continue
                    dir_list.append(os.path.join(root, d))
        except Exception:
            pass

        # Delete files
        for fp in file_list:
            try:
                # Remove read-only if present
                os.chmod(fp, 0o777)
                sz = os.path.getsize(fp)
                os.remove(fp)
                freed_bytes += sz
                deleted_count += 1
            except (PermissionError, OSError, FileNotFoundError):
                skipped_count += 1

        # Delete empty subdirectories (keep base_path itself)
        for dp in dir_list:
            if dp == base_path:
                continue
            try:
                os.rmdir(dp)
            except Exception:
                pass

    if log_cb:
        log_cb(f"  → 완료: {format_bytes(freed_bytes)} 확보 ({deleted_count}개 삭제, {skipped_count}개 사용 중으로 안전 건너뜀)")

    return freed_bytes, deleted_count, skipped_count

