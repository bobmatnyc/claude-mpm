"""Manifest fetcher for agent repository manifests.

Fetches agents-manifest.yaml from a remote agent repository source URL,
normalising the URL to point at the repository root regardless of any
subdirectory path appended during agent discovery.

Supported source URL forms (Phase 2):
  - GitHub raw:     https://raw.githubusercontent.com/<owner>/<repo>/<branch>[/...]
  - GitLab raw:     https://gitlab.com/<owner>/<repo>/-/raw/<branch>[/...]
  - Bitbucket raw:  https://bitbucket.org/<owner>/<repo>/raw/<branch>[/...]
  - Local path:     /absolute/path/to/dir  or  file:///absolute/path/to/dir
"""

import logging
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# Maximum manifest size accepted from remote (1 MiB).
MAX_MANIFEST_SIZE: int = 1_048_576

# Default HTTP timeout in seconds for manifest fetches.
MANIFEST_FETCH_TIMEOUT: int = 5


class ManifestFetcher:
    """Fetches agents-manifest.yaml from a remote or local agent source URL.

    Supported URL forms:
    - GitHub raw:    https://raw.githubusercontent.com/<owner>/<repo>/<branch>[/...]
    - GitLab raw:    https://gitlab.com/<owner>/<repo>/-/raw/<branch>[/...]
    - Bitbucket raw: https://bitbucket.org/<owner>/<repo>/raw/<branch>[/...]
    - Local path:    /absolute/path  or  file:///absolute/path

    All other URL schemes are silently skipped with a debug-level log.

    The source URL passed to :meth:`fetch` is the agent-directory URL used
    during sync (which may include a subdirectory path such as
    ``…/main/agents``).  :meth:`_compute_manifest_url` strips the
    subdirectory portion so the manifest is always fetched from the
    repository root branch.

    Example::

        import requests
        fetcher = ManifestFetcher()
        with requests.Session() as session:
            content = fetcher.fetch(
                "https://raw.githubusercontent.com/owner/repo/main/agents",
                session,
            )
    """

    MANIFEST_FILENAME: str = "agents-manifest.yaml"

    def fetch(
        self,
        source_url: str,
        session: requests.Session,
        timeout: int = MANIFEST_FETCH_TIMEOUT,
    ) -> str | None:
        """Fetch manifest content from the repository root.

        Detects local filesystem paths (starting with "/" or "file://") and
        delegates to :meth:`fetch_local`.  All other URLs are handled via HTTP.

        Behaviour by HTTP response:
        - 200: returns decoded text if within size limit.
        - 304: returns None (treat as no manifest; debug log).
        - 404: returns None (manifest absent; debug log).
        - any other status: returns None (warning log).

        Network errors (Timeout, ConnectionError, generic RequestException)
        are all caught and treated as None (fail-open; warning log).

        Args:
            source_url: Source URL pointing at the agent directory.  May be a
                GitHub/GitLab/Bitbucket raw URL or a local filesystem path.
                The subdirectory is automatically stripped so the manifest is
                resolved at branch/repo root.
            session: An active :class:`requests.Session` to use for HTTP GETs.
                Callers are responsible for session lifecycle.
            timeout: HTTP request timeout in seconds (default 5).

        Returns:
            Manifest YAML text, or None if unavailable for any reason.
        """
        # Delegate local filesystem paths without making any HTTP request.
        if source_url.startswith("/") or source_url.startswith("file://"):
            return self.fetch_local(source_url)

        manifest_url = self._compute_manifest_url(source_url)
        if manifest_url is None:
            return None

        logger.debug("Fetching manifest from: %s", manifest_url)

        try:
            response = session.get(manifest_url, timeout=timeout, stream=True)
        except requests.Timeout:
            logger.warning(
                "Timeout fetching manifest from %s (timeout=%ds). "
                "Proceeding without manifest (fail-open).",
                manifest_url,
                timeout,
            )
            return None
        except requests.ConnectionError as exc:
            logger.warning(
                "Connection error fetching manifest from %s: %s. "
                "Proceeding without manifest (fail-open).",
                manifest_url,
                exc,
            )
            return None
        except requests.RequestException as exc:
            logger.warning(
                "Unexpected error fetching manifest from %s: %s. "
                "Proceeding without manifest (fail-open).",
                manifest_url,
                exc,
            )
            return None

        if response.status_code == 304:
            logger.debug(
                "Manifest at %s returned 304 Not Modified; treating as absent.",
                manifest_url,
            )
            return None

        if response.status_code == 404:
            logger.debug(
                "Manifest not found at %s (404); repository has no manifest.",
                manifest_url,
            )
            return None

        if response.status_code != 200:
            logger.warning(
                "Unexpected HTTP %d fetching manifest from %s. "
                "Proceeding without manifest (fail-open).",
                response.status_code,
                manifest_url,
            )
            return None

        # Guard against oversized manifests using streaming to avoid
        # buffering arbitrarily large responses into memory.
        chunks: list[bytes] = []
        bytes_read = 0
        try:
            for chunk in response.iter_content(chunk_size=8192):
                bytes_read += len(chunk)
                if bytes_read > MAX_MANIFEST_SIZE:
                    response.close()
                    logger.warning(
                        "Manifest at %s exceeds %d-byte limit (read %d bytes so far). "
                        "Aborting download (fail-open).",
                        manifest_url,
                        MAX_MANIFEST_SIZE,
                        bytes_read,
                    )
                    return None
                chunks.append(chunk)
        except Exception as exc:
            logger.warning(
                "Error reading manifest body from %s: %s. "
                "Proceeding without manifest (fail-open).",
                manifest_url,
                exc,
            )
            return None

        return b"".join(chunks).decode("utf-8", errors="replace")

    def fetch_local(self, source_url: str) -> str | None:
        """Read manifest content from a local filesystem path.

        Accepts either a bare absolute path (``/path/to/dir``) or a
        ``file://`` URI (``file:///path/to/dir``).  The manifest filename
        is resolved relative to the given directory.

        Args:
            source_url: Absolute directory path or ``file://`` URI.

        Returns:
            Manifest YAML text, or None if the file is not found or cannot
            be read.
        """
        # Normalise file:// URI to a bare path.
        if source_url.startswith("file://"):
            bare = source_url[len("file://") :]
        else:
            bare = source_url

        manifest_path = Path(bare) / self.MANIFEST_FILENAME
        logger.debug("Reading local manifest from: %s", manifest_path)

        if not manifest_path.exists():
            logger.debug(
                "Local manifest not found at %s; treating as absent (fail-open).",
                manifest_path,
            )
            return None

        try:
            content = manifest_path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning(
                "Could not read local manifest at %s: %s. "
                "Proceeding without manifest (fail-open).",
                manifest_path,
                exc,
            )
            return None

        if len(content.encode("utf-8")) > MAX_MANIFEST_SIZE:
            logger.warning(
                "Local manifest at %s exceeds %d-byte limit. "
                "Skipping manifest (fail-open).",
                manifest_path,
                MAX_MANIFEST_SIZE,
            )
            return None

        return content

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _compute_manifest_url(self, source_url: str) -> str | None:
        """Derive the manifest URL from an agent source URL.

        Supported URL forms:

        GitHub raw::

            https://raw.githubusercontent.com/<owner>/<repo>/<branch>[/...]
            → https://raw.githubusercontent.com/<owner>/<repo>/<branch>/agents-manifest.yaml

        GitLab raw::

            https://gitlab.com/<owner>/<repo>/-/raw/<branch>[/...]
            → https://gitlab.com/<owner>/<repo>/-/raw/<branch>/agents-manifest.yaml

        Bitbucket raw::

            https://bitbucket.org/<owner>/<repo>/raw/<branch>[/...]
            → https://bitbucket.org/<owner>/<repo>/raw/<branch>/agents-manifest.yaml

        Any other URL scheme causes None to be returned.

        Args:
            source_url: Agent source URL, potentially including a
                subdirectory suffix (e.g. ``/agents`` or ``/agents/v2``).

        Returns:
            Full URL to ``agents-manifest.yaml``, or None if the URL is
            not a supported remote URL.

        Examples:
            >>> fetcher = ManifestFetcher()
            >>> fetcher._compute_manifest_url(
            ...     "https://raw.githubusercontent.com/owner/repo/main/agents"
            ... )
            'https://raw.githubusercontent.com/owner/repo/main/agents-manifest.yaml'
            >>> fetcher._compute_manifest_url(
            ...     "https://gitlab.com/owner/repo/-/raw/main/agents"
            ... )
            'https://gitlab.com/owner/repo/-/raw/main/agents-manifest.yaml'
            >>> fetcher._compute_manifest_url(
            ...     "https://bitbucket.org/owner/repo/raw/main/agents"
            ... )
            'https://bitbucket.org/owner/repo/raw/main/agents-manifest.yaml'
        """
        # ── GitHub raw ──────────────────────────────────────────────────
        raw_host = "raw.githubusercontent.com/"
        if raw_host in source_url:
            try:
                _, path_part = source_url.split(raw_host, 1)
            except ValueError:
                logger.debug("Could not parse GitHub raw URL: %s", source_url)
                return None

            segments = path_part.strip("/").split("/")
            if len(segments) < 3:
                logger.debug(
                    "GitHub raw URL '%s' does not have enough path segments "
                    "(owner/repo/branch required); cannot compute manifest URL.",
                    source_url,
                )
                return None

            owner, repo, branch = segments[0], segments[1], segments[2]
            return f"https://{raw_host}{owner}/{repo}/{branch}/{self.MANIFEST_FILENAME}"

        # ── GitLab raw ───────────────────────────────────────────────────
        # Form: https://gitlab.com/<owner>/<repo>/-/raw/<branch>[/subdir...]
        gitlab_host = "gitlab.com/"
        gitlab_raw_marker = "/-/raw/"
        if gitlab_host in source_url and gitlab_raw_marker in source_url:
            try:
                before_raw, after_raw = source_url.split(gitlab_raw_marker, 1)
                _, owner_repo = before_raw.split(gitlab_host, 1)
            except ValueError:
                logger.debug("Could not parse GitLab raw URL: %s", source_url)
                return None

            # after_raw: <branch>[/optional/subdirs...]
            branch_segments = after_raw.strip("/").split("/")
            if not branch_segments or not branch_segments[0]:
                logger.debug(
                    "GitLab raw URL '%s' is missing branch; cannot compute manifest URL.",
                    source_url,
                )
                return None

            branch = branch_segments[0]
            owner_repo = owner_repo.strip("/")
            return (
                f"https://{gitlab_host}{owner_repo}{gitlab_raw_marker}"
                f"{branch}/{self.MANIFEST_FILENAME}"
            )

        # ── Bitbucket raw ────────────────────────────────────────────────
        # Form: https://bitbucket.org/<owner>/<repo>/raw/<branch>[/subdir...]
        bitbucket_host = "bitbucket.org/"
        bitbucket_raw_marker = "/raw/"
        if bitbucket_host in source_url and bitbucket_raw_marker in source_url:
            try:
                before_raw, after_raw = source_url.split(bitbucket_raw_marker, 1)
                _, owner_repo = before_raw.split(bitbucket_host, 1)
            except ValueError:
                logger.debug("Could not parse Bitbucket raw URL: %s", source_url)
                return None

            branch_segments = after_raw.strip("/").split("/")
            if not branch_segments or not branch_segments[0]:
                logger.debug(
                    "Bitbucket raw URL '%s' is missing branch; cannot compute manifest URL.",
                    source_url,
                )
                return None

            branch = branch_segments[0]
            owner_repo = owner_repo.strip("/")
            return (
                f"https://{bitbucket_host}{owner_repo}{bitbucket_raw_marker}"
                f"{branch}/{self.MANIFEST_FILENAME}"
            )

        # ── Unsupported ──────────────────────────────────────────────────
        logger.debug(
            "Source URL '%s' is not a supported remote URL "
            "(GitHub/GitLab/Bitbucket raw URLs supported).",
            source_url,
        )
        return None
