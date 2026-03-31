"""
Cloudinary MCP Server
=====================
Cloudinary API를 활용한 이미지/미디어 에셋 관리 MCP 서버.

기존 blind-to-x 파이프라인의 Cloudinary 업로드 로직을 MCP로 노출합니다.

Tools:
  - upload_image: 로컬 이미지를 Cloudinary에 업로드
  - list_assets: 폴더별 에셋 목록 조회
  - get_asset_info: 에셋 상세 정보 조회
  - generate_url: 변환/최적화된 CDN URL 생성
  - get_usage_stats: 계정 사용량 확인

환경 변수:
  - CLOUDINARY_CLOUD_NAME
  - CLOUDINARY_API_KEY
  - CLOUDINARY_API_SECRET

Usage:
    python server.py
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    import cloudinary
    import cloudinary.api
    import cloudinary.uploader

    _HAS_CLOUDINARY = True
except ImportError:
    _HAS_CLOUDINARY = False

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None

# ─── 환경 설정 ────────────────────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


def _configure() -> None:
    """Cloudinary SDK를 환경 변수로 설정합니다."""
    if not _HAS_CLOUDINARY:
        raise ImportError("cloudinary 패키지가 설치되지 않았습니다: pip install cloudinary")

    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "").strip()
    api_key = os.getenv("CLOUDINARY_API_KEY", "").strip()
    api_secret = os.getenv("CLOUDINARY_API_SECRET", "").strip()

    if not all([cloud_name, api_key, api_secret]):
        raise ValueError(
            "Cloudinary 환경 변수가 설정되지 않았습니다. "
            "CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET 필요"
        )

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )


# ─── 도구 함수 ────────────────────────────────────────────────────────────────


def _upload_image(
    file_path: str,
    folder: str = "vibe-coding",
    public_id: str = "",
    tags: str = "",
) -> dict[str, Any]:
    """로컬 이미지를 Cloudinary에 업로드합니다.

    Args:
        file_path: 업로드할 이미지 파일 경로
        folder: Cloudinary 폴더 (기본: vibe-coding)
        public_id: 커스텀 public_id (비워두면 자동 생성)
        tags: 쉼표 구분 태그 문자열
    """
    try:
        _configure()
        path = Path(file_path)
        if not path.exists():
            return {"error": f"파일을 찾을 수 없습니다: {file_path}"}
        if not path.is_file():
            return {"error": f"경로가 파일이 아닙니다: {file_path}"}

        params: dict[str, Any] = {"folder": folder}
        if public_id:
            params["public_id"] = public_id
        if tags:
            params["tags"] = [t.strip() for t in tags.split(",")]

        result = cloudinary.uploader.upload(str(path), **params)

        return {
            "success": True,
            "public_id": result.get("public_id", ""),
            "secure_url": result.get("secure_url", ""),
            "url": result.get("url", ""),
            "format": result.get("format", ""),
            "width": result.get("width", 0),
            "height": result.get("height", 0),
            "bytes": result.get("bytes", 0),
            "created_at": result.get("created_at", ""),
            "retrieved_at": datetime.now().isoformat(),
        }
    except ImportError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"업로드 실패: {e}"}


def _list_assets(
    folder: str = "vibe-coding",
    max_results: int = 30,
    resource_type: str = "image",
) -> dict[str, Any]:
    """Cloudinary 폴더의 에셋 목록을 조회합니다."""
    try:
        _configure()
        result = cloudinary.api.resources(
            type="upload",
            prefix=folder,
            resource_type=resource_type,
            max_results=min(max_results, 100),
        )

        assets = []
        for r in result.get("resources", []):
            assets.append(
                {
                    "public_id": r.get("public_id", ""),
                    "secure_url": r.get("secure_url", ""),
                    "format": r.get("format", ""),
                    "width": r.get("width", 0),
                    "height": r.get("height", 0),
                    "bytes": r.get("bytes", 0),
                    "created_at": r.get("created_at", ""),
                }
            )

        return {
            "folder": folder,
            "count": len(assets),
            "assets": assets,
            "retrieved_at": datetime.now().isoformat(),
        }
    except ImportError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"에셋 목록 조회 실패: {e}"}


def _get_asset_info(public_id: str) -> dict[str, Any]:
    """특정 에셋의 상세 정보를 조회합니다."""
    try:
        _configure()
        result = cloudinary.api.resource(public_id)
        return {
            "public_id": result.get("public_id", ""),
            "secure_url": result.get("secure_url", ""),
            "format": result.get("format", ""),
            "resource_type": result.get("resource_type", ""),
            "width": result.get("width", 0),
            "height": result.get("height", 0),
            "bytes": result.get("bytes", 0),
            "created_at": result.get("created_at", ""),
            "tags": result.get("tags", []),
            "folder": result.get("folder", ""),
            "retrieved_at": datetime.now().isoformat(),
        }
    except ImportError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"에셋 정보 조회 실패: {e}"}


def _generate_url(
    public_id: str,
    width: int = 0,
    height: int = 0,
    crop: str = "fill",
    format: str = "auto",
    quality: str = "auto",
) -> dict[str, Any]:
    """변환/최적화된 Cloudinary CDN URL을 생성합니다."""
    try:
        _configure()
        transformations: list[dict] = []

        if width or height:
            t: dict[str, Any] = {"crop": crop}
            if width:
                t["width"] = width
            if height:
                t["height"] = height
            transformations.append(t)

        transformations.append({"fetch_format": format, "quality": quality})

        url = cloudinary.CloudinaryImage(public_id).build_url(
            transformation=transformations,
            secure=True,
        )

        return {
            "public_id": public_id,
            "optimized_url": url,
            "transformations": {
                "width": width or "auto",
                "height": height or "auto",
                "crop": crop,
                "format": format,
                "quality": quality,
            },
        }
    except ImportError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"URL 생성 실패: {e}"}


def _get_usage_stats() -> dict[str, Any]:
    """Cloudinary 계정의 사용량 통계를 조회합니다."""
    try:
        _configure()
        result = cloudinary.api.usage()

        return {
            "plan": result.get("plan", "unknown"),
            "storage": {
                "usage_bytes": result.get("storage", {}).get("usage", 0),
                "limit_bytes": result.get("storage", {}).get("limit", 0),
                "used_pct": result.get("storage", {}).get("used_percent", 0),
            },
            "bandwidth": {
                "usage_bytes": result.get("bandwidth", {}).get("usage", 0),
                "limit_bytes": result.get("bandwidth", {}).get("limit", 0),
                "used_pct": result.get("bandwidth", {}).get("used_percent", 0),
            },
            "transformations": {
                "usage": result.get("transformations", {}).get("usage", 0),
                "limit": result.get("transformations", {}).get("limit", 0),
                "used_pct": result.get("transformations", {}).get("used_percent", 0),
            },
            "objects": {
                "usage": result.get("objects", {}).get("usage", 0),
                "limit": result.get("objects", {}).get("limit", 0),
            },
            "retrieved_at": datetime.now().isoformat(),
        }
    except ImportError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"사용량 조회 실패: {e}"}


# ─── MCP 서버 등록 ────────────────────────────────────────────────────────────

if FastMCP is not None:
    mcp = FastMCP(
        "cloudinary",
        instructions=(
            "Cloudinary 이미지/미디어 에셋 관리 MCP 서버. "
            "이미지 업로드, 에셋 목록/상세 조회, 최적화 URL 생성, 사용량 확인을 제공합니다."
        ),
    )

    @mcp.tool()
    def upload_image(
        file_path: str,
        folder: str = "vibe-coding",
        public_id: str = "",
        tags: str = "",
    ) -> dict[str, Any]:
        """로컬 이미지를 Cloudinary에 업로드합니다.

        Args:
            file_path: 업로드할 이미지 파일 절대 경로
            folder: Cloudinary 저장 폴더 (기본: vibe-coding)
            public_id: 커스텀 public_id (비워두면 자동 생성)
            tags: 쉼표 구분 태그 (예: "shorts,ai_tech")
        """
        return _upload_image(file_path, folder, public_id, tags)

    @mcp.tool()
    def list_assets(
        folder: str = "vibe-coding",
        max_results: int = 30,
        resource_type: str = "image",
    ) -> dict[str, Any]:
        """Cloudinary 폴더의 에셋 목록을 조회합니다.

        Args:
            folder: 조회할 폴더 경로
            max_results: 최대 결과 수 (1~100)
            resource_type: 리소스 타입 (image, video, raw)
        """
        return _list_assets(folder, max_results, resource_type)

    @mcp.tool()
    def get_asset_info(public_id: str) -> dict[str, Any]:
        """특정 에셋의 상세 정보를 조회합니다.

        Args:
            public_id: Cloudinary public_id
        """
        return _get_asset_info(public_id)

    @mcp.tool()
    def generate_url(
        public_id: str,
        width: int = 0,
        height: int = 0,
        crop: str = "fill",
        format: str = "auto",
        quality: str = "auto",
    ) -> dict[str, Any]:
        """변환/최적화된 CDN URL을 생성합니다.

        Args:
            public_id: Cloudinary public_id
            width: 리사이즈 너비 (0=원본)
            height: 리사이즈 높이 (0=원본)
            crop: 크롭 모드 (fill, fit, scale, crop, thumb)
            format: 포맷 (auto, webp, png, jpg)
            quality: 품질 (auto, 1-100)
        """
        return _generate_url(public_id, width, height, crop, format, quality)

    @mcp.tool()
    def get_usage_stats() -> dict[str, Any]:
        """Cloudinary 계정의 사용량 통계를 조회합니다."""
        return _get_usage_stats()

else:
    mcp = None
    upload_image = _upload_image
    list_assets = _list_assets
    get_asset_info = _get_asset_info
    generate_url = _generate_url
    get_usage_stats = _get_usage_stats


if __name__ == "__main__":
    if mcp is None:
        print("mcp 패키지 미설치. pip install 'mcp[cli]' 후 다시 실행하세요.")
    else:
        mcp.run()
