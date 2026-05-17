"""
Exports a Canva design and posts each page to Instagram as a story or carousel.
Required env vars:
  CANVA_ACCESS_TOKEN       - Canva API OAuth access token
  CANVA_DESIGN_ID          - Canva design ID (e.g. DAHElVEheQw)
  INSTAGRAM_ACCESS_TOKEN   - Meta Graph API long-lived access token
  INSTAGRAM_USER_ID        - Instagram Business Account user ID
  POST_TYPE                - "story" or "feed" (default: story)
  CAPTION                  - Caption text for feed posts (optional)
"""

import os
import sys
import time
import requests

CANVA_API = "https://api.canva.com/rest/v1"
GRAPH_API = "https://graph.facebook.com/v19.0"

CANVA_TOKEN = os.environ["CANVA_ACCESS_TOKEN"]
DESIGN_ID = os.environ["CANVA_DESIGN_ID"]
IG_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
IG_USER_ID = os.environ["INSTAGRAM_USER_ID"]
POST_TYPE = os.environ.get("POST_TYPE", "story").lower()
CAPTION = os.environ.get("CAPTION", "")

CANVA_HEADERS = {"Authorization": f"Bearer {CANVA_TOKEN}"}


def export_design(design_id: str) -> list[str]:
    """Start a Canva export job and return the download URLs for each page."""
    resp = requests.post(
        f"{CANVA_API}/exports",
        headers=CANVA_HEADERS,
        json={
            "design_id": design_id,
            "format": {"type": "jpg", "export_quality": "pro"},
        },
    )
    resp.raise_for_status()
    job = resp.json()["job"]
    job_id = job["id"]

    # Poll until done
    for _ in range(30):
        time.sleep(5)
        status_resp = requests.get(
            f"{CANVA_API}/exports/{job_id}", headers=CANVA_HEADERS
        )
        status_resp.raise_for_status()
        job = status_resp.json()["job"]
        if job["status"] == "success":
            return [page["url"] for page in job["urls"]]
        if job["status"] == "failed":
            raise RuntimeError(f"Canva export failed: {job}")

    raise TimeoutError("Canva export timed out after 150 s")


def create_ig_container(image_url: str, is_story: bool, caption: str = "") -> str:
    """Create an Instagram media container and return its ID."""
    params = {
        "image_url": image_url,
        "access_token": IG_TOKEN,
    }
    if is_story:
        params["media_type"] = "STORIES"
    elif caption:
        params["caption"] = caption

    resp = requests.post(f"{GRAPH_API}/{IG_USER_ID}/media", params=params)
    resp.raise_for_status()
    return resp.json()["id"]


def publish_ig_container(container_id: str) -> str:
    """Publish an Instagram media container and return the media ID."""
    resp = requests.post(
        f"{GRAPH_API}/{IG_USER_ID}/media_publish",
        params={"creation_id": container_id, "access_token": IG_TOKEN},
    )
    resp.raise_for_status()
    return resp.json()["id"]


def wait_for_container(container_id: str) -> None:
    """Wait until an Instagram media container is ready."""
    for _ in range(12):
        resp = requests.get(
            f"{GRAPH_API}/{container_id}",
            params={"fields": "status_code", "access_token": IG_TOKEN},
        )
        resp.raise_for_status()
        status = resp.json().get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Container {container_id} errored")
        time.sleep(10)
    raise TimeoutError("Instagram container not ready after 120 s")


def post_as_stories(image_urls: list[str]) -> None:
    for i, url in enumerate(image_urls, 1):
        print(f"Posting story {i}/{len(image_urls)} …")
        cid = create_ig_container(url, is_story=True)
        wait_for_container(cid)
        media_id = publish_ig_container(cid)
        print(f"  Story posted: {media_id}")
        if i < len(image_urls):
            time.sleep(3)


def post_as_carousel(image_urls: list[str], caption: str) -> None:
    child_ids = []
    for i, url in enumerate(image_urls, 1):
        print(f"Creating carousel child {i}/{len(image_urls)} …")
        resp = requests.post(
            f"{GRAPH_API}/{IG_USER_ID}/media",
            params={
                "image_url": url,
                "is_carousel_item": "true",
                "access_token": IG_TOKEN,
            },
        )
        resp.raise_for_status()
        child_ids.append(resp.json()["id"])

    print("Creating carousel container …")
    resp = requests.post(
        f"{GRAPH_API}/{IG_USER_ID}/media",
        params={
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
            "access_token": IG_TOKEN,
        },
    )
    resp.raise_for_status()
    carousel_id = resp.json()["id"]
    wait_for_container(carousel_id)
    media_id = publish_ig_container(carousel_id)
    print(f"Carousel posted: {media_id}")


def main() -> None:
    print(f"Exporting Canva design {DESIGN_ID} …")
    image_urls = export_design(DESIGN_ID)
    print(f"Got {len(image_urls)} page(s)")

    if POST_TYPE == "story":
        post_as_stories(image_urls)
    else:
        post_as_carousel(image_urls, CAPTION)

    print("Done.")


if __name__ == "__main__":
    main()
