"""
Quark cloud drive client.
Uses quarkpan library for API operations, with raw HTTP fallback.
"""

import json
import re
import time
from pathlib import Path
from typing import Optional

import httpx

QUARK_API = "https://drive-pc.quark.cn/1/clouddrive"
QUARK_SHARE_API = "https://drive.quark.cn/1/clouddrive"
PROJECT_DIR = Path(__file__).resolve().parent.parent
COOKIE_CACHE = PROJECT_DIR / ".cache" / "quark_cookies.json"

# Try importing quarkpan for reliable API operations
try:
    from quark_client import create_client as _qp_create_client
    _HAS_QUARKPAN = True
except ImportError:
    _HAS_QUARKPAN = False


class QuarkClient:
    """Quark cloud drive client. Uses quarkpan if available, raw HTTP otherwise."""

    def __init__(self, username: str = "", password: str = "", cookie: str = ""):
        self.username = username
        self.password = password
        self._cookie = cookie
        self._qp_client = None
        self.client = httpx.Client(
            follow_redirects=True,
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://pan.quark.cn/",
            },
        )

    @property
    def cookie(self) -> str:
        if self._cookie:
            return self._cookie
        self._load_cookie_cache()
        return self._cookie

    def _load_cookie_cache(self):
        if COOKIE_CACHE.exists():
            try:
                data = json.loads(COOKIE_CACHE.read_text(encoding='utf-8'))
                if data.get("expires_at", 0) > time.time():
                    self._cookie = data.get("cookie", "")
            except Exception:
                pass

    def _save_cookie_cache(self):
        COOKIE_CACHE.parent.mkdir(parents=True, exist_ok=True)
        COOKIE_CACHE.write_text(json.dumps({
            "cookie": self._cookie,
            "expires_at": time.time() + 86400 * 7,
        }, ensure_ascii=False), encoding='utf-8')

    def _get_qp(self):
        """Get or create quarkpan client."""
        if not _HAS_QUARKPAN:
            return None
        if self._qp_client is None and self._cookie:
            try:
                self._qp_client = _qp_create_client(cookies=self._cookie, auto_login=False)
            except Exception:
                pass
        return self._qp_client

    # ── Auth ──

    def qr_login(self) -> bool:
        """QR code login. Saves PNG + ASCII, polls for scan."""
        import uuid
        import sys as _sys
        import urllib.parse

        # Step 1: Get QR token
        try:
            r = self.client.get(
                "https://uop.quark.cn/cas/ajax/getTokenForQrcodeLogin",
                params={"client_id": "532", "v": "1.2", "request_id": str(uuid.uuid4())},
            )
            data = r.json()
            if data.get("status") != 2000000:
                print("获取二维码失败，请稍后重试", file=_sys.stderr)
                return False
            token = data.get("data", {}).get("members", {}).get("token", "")
            if not token:
                print("获取二维码token失败", file=_sys.stderr)
                return False
        except Exception as e:
            print(f"获取二维码失败: {e}", file=_sys.stderr)
            return False

        # Step 2: Build QR URL and display
        qr_url = "https://su.quark.cn/4_eMHBJ?" + urllib.parse.urlencode({
            "token": token, "client_id": "532", "ssb": "weblogin",
            "uc_param_str": "",
            "uc_biz_str": "S:custom|OPT:SAREA@0|OPT:IMMERSIVE@1|OPT:BACK_BTN_STYLE@0",
        })
        self._display_qr(qr_url)

        print("请使用夸克 App 扫描上方二维码...", file=_sys.stderr)

        # Step 3: Poll
        for i in range(120):
            time.sleep(2)
            try:
                r = self.client.get(
                    "https://uop.quark.cn/cas/ajax/getServiceTicketByQrcodeToken",
                    params={"client_id": "532", "v": "1.2", "token": token,
                            "request_id": str(uuid.uuid4())},
                )
                result = r.json()
                status = result.get("status")

                if status == 2000000:
                    # Extract service ticket
                    service_ticket = result.get("data", {}).get("members", {}).get("service_ticket", "")
                    # Collect initial cookies from UOP response
                    initial = {k: v for k, v in r.cookies.items()}
                    if service_ticket:
                        # Exchange for full session cookies
                        cookie_str = self._enrich_cookie(service_ticket, initial)
                        if cookie_str:
                            self._cookie = cookie_str
                            self._save_cookie_cache()
                            print("✅ 扫码登录成功！", file=_sys.stderr)
                            return True
                    elif initial:
                        cookie_str = "; ".join(f"{k}={v}" for k, v in initial.items())
                        self._cookie = cookie_str
                        self._save_cookie_cache()
                        print("✅ 扫码登录成功！", file=_sys.stderr)
                        return True
                elif status == 2100102:
                    if i % 5 == 0:
                        print("  已扫描，请在手机上确认...", file=_sys.stderr)
                elif status in (2100103, 2100104):
                    print("❌ 二维码已过期，请重新运行", file=_sys.stderr)
                    return False
            except Exception:
                pass

        print("⏰ 登录超时（4分钟）", file=_sys.stderr)
        return False

    def _enrich_cookie(self, service_ticket: str, initial_cookies: dict = None) -> str:
        """Exchange UOP service ticket for full pan.quark.cn session cookies."""
        try:
            client = httpx.Client(
                headers={"User-Agent": "Mozilla/5.0"},
                follow_redirects=True,
            )
            # Set initial cookies if provided
            if initial_cookies:
                for k, v in initial_cookies.items():
                    client.cookies.set(k, v, domain="pan.quark.cn")

            # Exchange service ticket for proper session cookies
            client.get("https://pan.quark.cn/account/info", params={
                "st": service_ticket,
                "lw": "scan",
            }, timeout=15)

            # Collect all cookies
            return "; ".join(f"{k}={v}" for k, v in client.cookies.items())
        except Exception:
            return ""

    def _display_qr(self, url: str):
        """Display QR via PNG > ASCII > URL."""
        import sys as _sys

        # Method 1: PNG
        try:
            import qrcode as qr_mod
            from qrcode.image.pil import PilImage
            img = qr_mod.make(url, image_factory=PilImage)
            png_path = PROJECT_DIR / ".cache" / "login_qr.png"
            png_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(str(png_path))
            print(f"📱 二维码已保存: {png_path}", file=_sys.stderr)
            print(f"   请打开该图片，用夸克 App 扫描", file=_sys.stderr)
            return
        except Exception:
            pass

        # Method 2: ASCII
        try:
            import qrcode as qr_mod
            qr = qr_mod.QRCode(border=2)
            qr.add_data(url)
            qr.make(fit=True)
            qr.print_ascii(invert=True)
            print("请使用夸克 App 扫描上方二维码...", file=_sys.stderr)
            return
        except Exception:
            pass

        # Method 3: URL
        print("⚠️  无法显示二维码，请使用以下链接生成二维码后扫码：", file=_sys.stderr)
        print(f"     {url}", file=_sys.stderr)
        print(f"     提示：复制链接到 https://cli.im 可在线生成二维码", file=_sys.stderr)

    def check_cookie(self) -> bool:
        if not self.cookie:
            return False
        try:
            r = self.client.get(
                "https://pan.quark.cn/account/info",
                headers={"Cookie": self.cookie},
                timeout=10,
            )
            return r.status_code == 200
        except Exception:
            return False

    # ── Save share ──

    def save_share(self, share_url: str, folder_name: str = "") -> dict:
        """Save a quark share link to drive."""
        if not self.cookie:
            return {"error": "Not logged in. Run: mediavault login"}

        # Primary: quarkpan (handles auth correctly)
        qp = self._get_qp()
        if qp:
            try:
                if folder_name:
                    return qp.save_shared_files(share_url, target_folder_name=folder_name)
                return qp.save_shared_files(share_url)
            except Exception as e:
                pass  # Fall back to raw

        # Fallback: raw HTTP
        return self._save_raw(share_url, folder_name)

    # ── Raw HTTP fallback ──

    def _save_raw(self, share_url: str, folder_name: str = "") -> dict:
        """Raw HTTP save implementation."""
        pwd_match = re.search(r"pan\.quark\.cn/s/([a-zA-Z0-9]+)", share_url)
        if not pwd_match:
            return {"error": "Invalid share URL"}

        pwd_id = pwd_match.group(1)
        headers = {"Cookie": self.cookie, "Content-Type": "application/json"}

        # Get share token
        r = self.client.post(
            f"{QUARK_SHARE_API}/share/sharepage/token",
            json={"pwd_id": pwd_id, "passcode": ""},
            headers=headers,
        )
        if r.status_code != 200 or r.json().get("code") != 0:
            return {"error": "Failed to get share token"}

        stoken = r.json()["data"]["stoken"]

        # List files
        r = self.client.get(
            f"{QUARK_SHARE_API}/share/sharepage/detail",
            params={"pwd_id": pwd_id, "stoken": stoken, "pdir_fid": "0",
                    "_page": "1", "_size": "50", "pr": "ucpro", "fr": "pc"},
            headers=headers,
        )
        if r.status_code != 200:
            return {"error": "Failed to list share files"}

        files = r.json().get("data", {}).get("list", [])
        if not files:
            return {"error": "Share is empty"}

        # Save
        save_body = {
            "fid_list": [f["fid"] for f in files],
            "fid_token_list": [f.get("share_fid_token", "") for f in files],
            "to_pdir_fid": "0",
            "pwd_id": pwd_id,
            "stoken": stoken,
            "pdir_fid": "0",
            "pdir_save_all": True,
            "exclude_fids": [],
            "scene": "link",
        }
        if folder_name:
            save_body["target_folder_name"] = folder_name

        r = self.client.post(
            f"{QUARK_SHARE_API}/share/sharepage/save",
            json=save_body, headers=headers,
        )
        return r.json() if r.status_code == 200 else {"error": f"Save failed: {r.status_code}"}

    # ── File operations ──

    def list_files(self, parent_id: str = "0") -> dict:
        qp = self._get_qp()
        if qp:
            try:
                return qp.list_files(parent_id)
            except Exception:
                pass
        r = self.client.get(
            f"{QUARK_API}/file",
            params={"pdir_fid": parent_id, "pr": "ucpro", "fr": "pc", "_size": "200"},
            headers={"Cookie": self.cookie},
        )
        return r.json() if r.status_code == 200 else {"data": {"list": []}}

    def create_folder(self, name: str, parent_id: str = "0") -> dict:
        qp = self._get_qp()
        if qp:
            try:
                return qp.create_folder(name, parent_id)
            except Exception:
                pass
        r = self.client.post(
            f"{QUARK_API}/file",
            json={"pdir_fid": parent_id, "file_name": name, "dir": True},
            headers={"Cookie": self.cookie, "Content-Type": "application/json"},
        )
        return r.json() if r.status_code == 200 else {"data": {}}

    def get_file_info(self, fid: str) -> dict:
        qp = self._get_qp()
        if qp:
            try:
                return qp.get_file_info(fid)
            except Exception:
                pass
        r = self.client.get(
            f"{QUARK_API}/file",
            params={"fid": fid, "pr": "ucpro", "fr": "pc"},
            headers={"Cookie": self.cookie},
        )
        return r.json() if r.status_code == 200 else {"data": {}}

    def rename_file(self, fid: str, name: str) -> dict:
        qp = self._get_qp()
        if qp:
            try:
                return qp.rename_file(fid, name)
            except Exception:
                pass
        r = self.client.post(
            f"{QUARK_API}/file/rename",
            json={"fid": fid, "file_name": name},
            headers={"Cookie": self.cookie, "Content-Type": "application/json"},
        )
        return r.json() if r.status_code == 200 else {}

    def move_files(self, fid_list: list, to_pdir_fid: str) -> dict:
        qp = self._get_qp()
        if qp:
            try:
                return qp.move_files(fid_list, to_pdir_fid)
            except Exception:
                pass
        body = {"fid_list": fid_list, "to_pdir_fid": to_pdir_fid}
        headers = {"Cookie": self.cookie, "Content-Type": "application/json"}
        for attempt in range(3):
            try:
                r = self.client.post(f"{QUARK_API}/file/move", json=body, headers=headers, timeout=60)
                if r.status_code == 200:
                    return r.json()
                r = self.client.post(f"{QUARK_API}/file/operator", json=body, headers=headers, timeout=60)
                if r.status_code == 200:
                    return r.json()
            except Exception:
                if attempt < 2:
                    time.sleep(2)
        return {}
