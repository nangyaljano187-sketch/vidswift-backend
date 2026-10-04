import os
from urllib.parse import urlparse

import httpx
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


SAVEAPI_URL = "https://api.saveapi.org/v1/download"

SUPPORTED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
    "m.youtube.com",

    "tiktok.com",
    "www.tiktok.com",
    "vm.tiktok.com",
    "vt.tiktok.com",

    "instagram.com",
    "www.instagram.com",

    "facebook.com",
    "www.facebook.com",
    "fb.watch",
}


def health(request):
    return JsonResponse({
        "ok": True,
        "service": "VidSwift Django API",
    })


def detect_platform(value: str):
    host = (urlparse(value).hostname or "").lower()

    for supported in SUPPORTED_HOSTS:
        if host == supported or host.endswith("." + supported):

            if "youtube" in supported or supported == "youtu.be":
                return "youtube"

            if "tiktok" in supported:
                return "tiktok"

            if "instagram" in supported:
                return "instagram"

            if supported in {
                "facebook.com",
                "www.facebook.com",
                "fb.watch",
            }:
                return "facebook"

    return None


def valid_http_url(value: str):
    try:
        parsed = urlparse(value)

        return (
            parsed.scheme in {"http", "https"}
            and bool(parsed.netloc)
        )

    except Exception:
        return False


def get_saveapi_key():
    return os.environ.get("SAVEAPI_KEY", "").strip()


def make_error(message, status=400, **extra):
    data = {
        "ok": False,
        "error": message,
    }

    data.update(extra)

    return JsonResponse(data, status=status)


def normalize_formats(data):
    """
    SaveAPI can return:
    - formats[] when multiple renditions exist
    - medias[] when direct media entries are returned

    Frontend expects:
    {
        format,
        label,
        type,
        url
    }
    """

    result = []

    # ---------------------------------------------------------
    # Case 1: SaveAPI returned formats[]
    # ---------------------------------------------------------
    saveapi_formats = data.get("formats")

    if isinstance(saveapi_formats, list):
        for item in saveapi_formats:
            if not isinstance(item, dict):
                continue

            url = str(item.get("url", "")).strip()

            if not valid_http_url(url):
                continue

            format_name = str(
                item.get("format")
                or item.get("ext")
                or item.get("type")
                or "original"
            ).strip()

            label = str(
                item.get("label")
                or format_name
            ).strip()

            media_type = str(
                item.get("type")
                or "video"
            ).strip().lower()

            result.append({
                "format": format_name,
                "label": label,
                "type": media_type,
                "url": url,
            })

    # ---------------------------------------------------------
    # Case 2: SaveAPI returned medias[]
    # ---------------------------------------------------------
    if not result:
        medias = data.get("medias")

        if isinstance(medias, list):
            for index, item in enumerate(medias):
                if not isinstance(item, dict):
                    continue

                url = str(item.get("url", "")).strip()

                if not valid_http_url(url):
                    continue

                media_type = str(
                    item.get("type")
                    or "video"
                ).strip().lower()

                ext = str(
                    item.get("ext")
                    or item.get("format")
                    or ""
                ).strip().lower()

                format_name = str(
                    item.get("format")
                    or ext
                    or f"media_{index + 1}"
                ).strip()

                if media_type == "audio" or ext in {
                    "mp3",
                    "m4a",
                    "aac",
                    "wav",
                    "ogg",
                }:
                    label = (
                        "MP3"
                        if ext == "mp3"
                        else f"Audio {ext.upper()}"
                        if ext
                        else "Audio"
                    )
                else:
                    label = str(
                        item.get("label")
                        or item.get("quality")
                        or format_name
                    ).strip()

                result.append({
                    "format": format_name,
                    "label": label,
                    "type": media_type,
                    "url": url,
                })

    return result


def get_title(data, platform):
    """
    SaveAPI metadata can differ by platform.
    Try common fields and then use a safe fallback.
    """

    candidates = [
        data.get("title"),
        data.get("name"),
        data.get("caption"),
    ]

    for value in candidates:
        if value:
            return str(value).strip()

    return f"{platform.title()} video"


def get_thumbnail(data):
    candidates = [
        data.get("thumbnail"),
        data.get("thumbnail_url"),
        data.get("cover"),
    ]

    for value in candidates:
        if value and valid_http_url(str(value)):
            return str(value)

    return ""


def get_primary_download_url(formats):
    """
    Pick the first valid direct media URL.
    """

    if not formats:
        return ""

    # Prefer video over audio as the main download URL.
    for item in formats:
        if item.get("type") == "video":
            return item.get("url", "")

    return formats[0].get("url", "")


def saveapi_error_message(response_data, status_code):
    """
    Convert SaveAPI's documented error envelope into
    a user-friendly message.
    """

    error = response_data.get("error")

    if isinstance(error, dict):
        code = str(error.get("code", "")).upper()
        message = str(
            error.get("message")
            or "SaveAPI request failed."
        )

        friendly = {
            "INVALID_URL": "The video URL is invalid.",
            "UNSUPPORTED_PLATFORM": "This platform is not supported.",
            "MISSING_API_KEY": "SaveAPI key is missing on the server.",
            "INVALID_API_KEY": "The SaveAPI key is invalid.",
            "KEY_REVOKED": "The SaveAPI key has been revoked.",
            "KEY_EXPIRED": "The SaveAPI key has expired.",
            "ACCOUNT_SUSPENDED": "The SaveAPI account is suspended.",
            "PLATFORM_NOT_ALLOWED": "This platform is not available on the current SaveAPI plan.",
            "PRIVATE_CONTENT": "This video is private and cannot be resolved.",
            "MEDIA_NOT_FOUND": "No downloadable media was found.",
            "LINK_EXPIRED": "The media link expired. Please try again.",
            "RATE_LIMITED": "Too many requests. Please wait a little and try again.",
            "QUOTA_EXCEEDED": "SaveAPI credits have been exhausted.",
            "UPSTREAM_ERROR": "The source platform temporarily failed. Please try again.",
            "UPSTREAM_TIMEOUT": "The source platform took too long to respond.",
            "INTERNAL_ERROR": "SaveAPI encountered an internal error.",
        }

        return friendly.get(code, message)

    return f"SaveAPI request failed with status {status_code}."


@csrf_exempt
def resolve_video(request):

    if request.method != "POST":
        return make_error(
            "POST required.",
            status=405,
        )

    # ---------------------------------------------------------
    # Read JSON body
    # ---------------------------------------------------------
    try:
        import json

        payload = json.loads(
            request.body or "{}"
        )

    except json.JSONDecodeError:
        return make_error(
            "Invalid JSON.",
            status=400,
        )

    # ---------------------------------------------------------
    # Get URL
    # ---------------------------------------------------------
    url = str(
        payload.get("url", "")
    ).strip()

    if not url:
        return make_error(
            "Video URL is required.",
            status=400,
        )

    # ---------------------------------------------------------
    # Validate URL
    # ---------------------------------------------------------
    if not valid_http_url(url):
        return make_error(
            "Only valid HTTP/HTTPS URLs are supported.",
            status=400,
        )

    # ---------------------------------------------------------
    # Detect supported platform
    # ---------------------------------------------------------
    platform = detect_platform(url)

    if not platform:
        return make_error(
            "Unsupported video platform. "
            "Supported: YouTube, TikTok, Instagram and Facebook.",
            status=400,
        )

    # ---------------------------------------------------------
    # SaveAPI key
    # ---------------------------------------------------------
    api_key = get_saveapi_key()

    if not api_key:
        return make_error(
            "SaveAPI is not configured on the server.",
            status=500,
        )

    # ---------------------------------------------------------
    # Call SaveAPI
    # ---------------------------------------------------------
    try:
        response = httpx.get(
            SAVEAPI_URL,
            params={
                "url": url,
            },
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            },
            timeout=30.0,
        )

    except httpx.TimeoutException:
        return make_error(
            "SaveAPI request timed out. Please try again.",
            status=504,
        )

    except httpx.RequestError:
        return make_error(
            "Could not connect to SaveAPI.",
            status=502,
        )

    # ---------------------------------------------------------
    # Parse SaveAPI JSON
    # ---------------------------------------------------------
    try:
        data = response.json()

    except ValueError:
        return make_error(
            "SaveAPI returned an invalid response.",
            status=502,
        )

    # ---------------------------------------------------------
    # SaveAPI failure
    # ---------------------------------------------------------
    if not response.is_success or data.get("success") is False:

        message = saveapi_error_message(
            data,
            response.status_code,
        )

        # Never expose the API key.
        return make_error(
            message,
            status=(
                response.status_code
                if 400 <= response.status_code < 600
                else 502
            ),
            stage="saveapi_error",
            platform=platform,
        )

    # ---------------------------------------------------------
    # Convert SaveAPI formats into frontend format
    # ---------------------------------------------------------
    formats = normalize_formats(data)

    if not formats:
        return make_error(
            "SaveAPI could not find a downloadable media file.",
            status=404,
            stage="media_not_found",
            platform=platform,
        )

    # ---------------------------------------------------------
    # Main download URL
    # ---------------------------------------------------------
    download_url = get_primary_download_url(formats)

    # ---------------------------------------------------------
    # Metadata
    # ---------------------------------------------------------
    title = get_title(
        data,
        platform,
    )

    thumbnail = get_thumbnail(data)

    # ---------------------------------------------------------
    # Final response for Netlify frontend
    # ---------------------------------------------------------
    return JsonResponse({
        "ok": True,
        "stage": "resolved",
        "platform": platform,

        "title": title,

        "thumbnail": thumbnail,

        "download_url": download_url,

        "formats": formats,

        "recommended_format": data.get(
            "recommended_format"
        ),

        "credits": data.get(
            "credits"
        ),
    })