from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, NamedTuple

import httpx

from app.concurrency import gather_all
from app.github.client import GitHubRateLimited
from app.github.queries import (
    EXTERNAL_PRS,
    EXTERNAL_REVIEW_COUNT,
    PINNED_REPOS,
    WORKFLOW_FORGES,
    external_merged_prs_query,
    workflow_files_query,
)
from app.models import Profile, Repo

if TYPE_CHECKING:
    from collections.abc import Collection

    from app.github.client import GitHubClient

logger = logging.getLogger(__name__)


class NotAnIndividualError(Exception):
    """Raised when /users/{login} resolves to an Organization (or other
    non-User account type). The dependency layer maps this to a 422
    so the frontend can render a specific message."""


# Commit messages are attacker-influenced; only a bounded prefix is examined.
_COMMIT_SUBJECT_MAX = 500
# One page of the user's commits per repo. A full page means older ones
# exist that ingestion never saw.
_COMMITS_PER_REPO = 100

# How many repos to inspect for README / tests / CI / deployment signals.
# Matches the cap used for language aggregation. Beyond this, signals are
# diminishing and the API cost is real.
ROOT_CONTENT_LIMIT = 20

# Root-listing heuristics. Names are compared lowercased. The sets follow the
# 2026-10-13 research (each tool's own docs) and favour precision: names that
# collide with unrelated projects (app.json is also Expo's config,
# template.yaml is generic, `specs/` holds spec-driven-development docs) stay
# out, and so do dead services (Cirrus CI shut down on 2026-06-01).
_TEST_DIRS = frozenset(
    {"tests", "test", "__tests__", "spec", "e2e", "cypress", "integration_test", "t", "testdata"}
)
_TEST_FILES = frozenset(
    {
        "cypress.json",
        "pytest.ini",
        ".pytest.ini",
        "pytest.toml",
        ".pytest.toml",
        "conftest.py",
        "tox.ini",
        "tox.toml",
        "noxfile.py",
        "phpunit.xml",
        "phpunit.dist.xml",
        "phpunit.xml.dist",
        ".rspec",
        "dart_test.yaml",
    }
)
_TEST_FILE_PREFIXES = (
    "vitest.config.",
    "vitest.workspace.",
    "jest.config.",
    "playwright.config.",
    "cypress.config.",
    "karma.conf.",
    ".mocharc.",
)
_VITEST_PROJECT_CONFIG = re.compile(r"^vitest\.[\w-]+\.config\.")
# Go test files sit beside the code. .NET test projects are `<Name>.Tests`
# directories; as a file name the suffix is something else (`.env.test`).
_TEST_FILE_SUFFIXES = ("_test.go",)
_TEST_DIR_SUFFIXES = (".tests", ".test")

_CI_MARKERS = frozenset(
    {
        ".gitlab-ci.yml",
        "azure-pipelines.yml",
        ".azure-pipelines.yml",
        "bitbucket-pipelines.yml",
        "jenkinsfile",
        ".circleci",
        ".travis.yml",
        ".drone.yml",
        ".woodpecker.yml",
        ".woodpecker.yaml",
        ".woodpecker",
        "buildkite.yml",
        "buildkite.yaml",
        "buildkite.json",
        ".buildkite",
        "appveyor.yml",
        ".appveyor.yml",
        ".semaphore",
        "codemagic.yaml",
        "bitrise.yml",
        "cloudbuild.yaml",
        "cloudbuild.yml",
        "cloudbuild.json",
        "buildspec.yml",
        ".tekton",
        ".teamcity",
    }
)
# These directories hold CI only when their `workflows/` subdirectory has a
# .yml/.yaml file; on their own they often carry just FUNDING.yml, issue
# templates, dependabot.yml or assistant instructions. _probe_workflow_files
# checks every candidate repo in one GraphQL query.
_WORKFLOW_DIRS = tuple(path for _alias, path in WORKFLOW_FORGES)
_WORKFLOW_FILE_SUFFIXES = (".yml", ".yaml")

_DEPLOYMENT_MARKERS: dict[str, str] = {
    "dockerfile": "dockerfile",
    "containerfile": "containerfile",
    "compose.yaml": "docker-compose",
    "compose.yml": "docker-compose",
    "docker-compose.yaml": "docker-compose",
    "docker-compose.yml": "docker-compose",
    "vercel.json": "vercel",
    "vercel.toml": "vercel",
    "vercel.ts": "vercel",
    "vercel.mts": "vercel",
    "vercel.js": "vercel",
    "vercel.mjs": "vercel",
    "vercel.cjs": "vercel",
    "netlify.toml": "netlify",
    "fly.toml": "fly",
    "render.yaml": "render",
    "railway.json": "railway",
    "railway.toml": "railway",
    ".railway": "railway",
    "wrangler.toml": "cloudflare",
    "wrangler.json": "cloudflare",
    "wrangler.jsonc": "cloudflare",
    "procfile": "heroku",
    "heroku.yml": "heroku",
    "serverless.yml": "serverless",
    "serverless.yaml": "serverless",
    "serverless.ts": "serverless",
    "serverless.js": "serverless",
    "serverless.json": "serverless",
    "sst.config.ts": "sst",
    "amplify.yml": "amplify",
    "firebase.json": "firebase",
    ".firebaserc": "firebase",
    "samconfig.toml": "aws-sam",
    "cdk.json": "aws-cdk",
    "appspec.yml": "aws-codedeploy",
    ".ebextensions": "elastic-beanstalk",
    "apprunner.yaml": "aws-app-runner",
    "pulumi.yaml": "pulumi",
    "pulumi.yml": "pulumi",
    "main.tf": "terraform",
    ".terraform.lock.hcl": "terraform",
    "chart.yaml": "helm",
    "helmfile.yaml": "helmfile",
    "helmfile.yaml.gotmpl": "helmfile",
    "helmfile.d": "helmfile",
    "kustomization.yaml": "kustomize",
    "kustomization.yml": "kustomize",
    "kustomization": "kustomize",
    "skaffold.yaml": "skaffold",
    "railpack.json": "railpack",
    "nixpacks.toml": "nixpacks",
    ".do": "digitalocean",
    "zbpack.json": "zeabur",
    "captain-definition": "caprover",
    ".kamal": "kamal",
    "staticwebapp.config.json": "azure-static-web-apps",
    "azure.yaml": "azure-developer-cli",
    ".upsun": "upsun",
    ".platform.app.yaml": "platform-sh",
    "app.yaml": "app-engine",
}


# Root dependency manifests (2026-10-13 research). Lockfiles (manifest.toml is
# Julia's and Gleam's) and build files whose dependencies live elsewhere
# (stack.yaml, build.zig, settings.gradle) are not manifests. Each maps to the
# label shown as evidence: exact names as their ecosystem spells them.
_MANIFEST_FILES: dict[str, str] = {
    name.lower(): name
    for name in (
        "package.json",
        "pyproject.toml",
        "requirements.txt",
        "Pipfile",
        "setup.py",
        "setup.cfg",
        "environment.yml",
        "Cargo.toml",
        "go.mod",
        "Gemfile",
        "composer.json",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "build.sbt",
        "Package.swift",
        "Podfile",
        "pubspec.yaml",
        "mix.exs",
        "deno.json",
        "deno.jsonc",
        "Directory.Packages.props",
        "packages.config",
        "build.zig.zon",
        "gleam.toml",
        "opam",
        "Project.toml",
        "DESCRIPTION",
        "rebar.config",
        "vcpkg.json",
        "conanfile.txt",
        "conanfile.py",
        "shard.yml",
        "deps.edn",
        "project.clj",
        "elm.json",
        "dub.json",
        "dub.sdl",
        "fpm.toml",
        "alire.toml",
        "Scarb.toml",
        "Move.toml",
        "lakefile.lean",
        "lakefile.toml",
        "MODULE.bazel",
        "flake.nix",
    )
}
# Manifests named after their project. The label is the kind alone: labels
# reach the narrator's prompt, and the rest of the name is free text.
_MANIFEST_SUFFIXES = (".csproj", ".fsproj", ".vbproj", ".cabal", ".opam", ".gemspec", ".nimble")


def _manifest_label(name: str) -> str | None:
    lowered = name.lower()
    if lowered in _MANIFEST_FILES:
        return _MANIFEST_FILES[lowered]
    suffix = next((s for s in _MANIFEST_SUFFIXES if lowered.endswith(s)), None)
    return f"*{suffix}" if suffix else None


def _manifests(names: list[str]) -> list[str]:
    """Labels for the dependency manifests among root entry names, sorted."""
    labels = {label for name in names if (label := _manifest_label(name))}
    return sorted(labels, key=str.lower)


class RootSignals(NamedTuple):
    has_readme: bool
    has_tests: bool
    has_ci: bool
    deployment_hints: list[str]
    # Of _WORKFLOW_DIRS, the ones present: CI only if their workflows/ hold files.
    workflow_dirs: tuple[str, ...]


def _is_test_entry(name: str, *, is_dir: bool) -> bool:
    return (
        name in _TEST_DIRS
        or name in _TEST_FILES
        or name.startswith(_TEST_FILE_PREFIXES)
        or _VITEST_PROJECT_CONFIG.match(name) is not None
        or name.endswith(_TEST_FILE_SUFFIXES)
        or (is_dir and name.endswith(_TEST_DIR_SUFFIXES))
    )


def _classify_root_entries(entries: list[str], *, dir_names: Collection[str] = ()) -> RootSignals:
    """Derive README / tests / CI / deployment signals from root entry names.
    `dir_names` are the entries that are directories."""
    lowered = {entry.lower() for entry in entries}
    lowered_dirs = {name.lower() for name in dir_names}
    hints = [hint for marker, hint in _DEPLOYMENT_MARKERS.items() if marker in lowered]
    if any(name.endswith(".tf") for name in lowered):
        hints.append("terraform")
    # Preserve insertion order, dedupe (e.g. compose.yaml + docker-compose.yml).
    seen: set[str] = set()
    unique_hints = [h for h in hints if not (h in seen or seen.add(h))]
    return RootSignals(
        has_readme=any(entry.startswith("readme") for entry in lowered),
        has_tests=any(_is_test_entry(name, is_dir=name in lowered_dirs) for name in lowered),
        has_ci=bool(lowered & _CI_MARKERS),
        deployment_hints=unique_hints,
        workflow_dirs=tuple(d for d in _WORKFLOW_DIRS if d in lowered),
    )


_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)


def _visible_chars(markdown: str | None) -> int:
    """Length of the text a visitor sees. GitHub's starter profile README is
    almost entirely an HTML comment, so a raw length credits untouched ones."""
    return len(_HTML_COMMENT.sub("", markdown or "").strip())


def _commit_day(commit: dict[str, Any]) -> datetime | None:
    """The commit's author date as a UTC-aware day, so date math stays safe."""
    date_str = (commit.get("author") or {}).get("date")
    if not date_str:
        return None
    return datetime.strptime(date_str[:10], "%Y-%m-%d").replace(tzinfo=UTC)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _repo_from_rest(raw: dict[str, Any]) -> Repo:
    return Repo(
        name=raw["name"],
        full_name=raw["full_name"],
        primary_language=raw.get("language"),
        stars=raw.get("stargazers_count", 0),
        forks=raw.get("forks_count", 0),
        is_fork=raw.get("fork", False),
        has_readme=False,
        has_tests=False,
        has_ci=False,
        deployment_hints=[],
        size_kb=raw.get("size", 0),
        last_commit_at=_parse_dt(raw.get("pushed_at")),
        created_at=_parse_dt(raw.get("created_at")) or datetime.now(UTC),
    )


async def _enrich_repo_signals(repo: Repo, gh: GitHubClient) -> tuple[str, ...]:
    """Inspect a repo's root contents and populate README/tests/CI/deployment
    flags. Returns the workflow directories present, for _probe_workflow_files.

    A repository GitHub won't serve (empty, DMCA'd, blocked) reads as an empty
    listing and keeps its conservative `False` flags. A rate limit or a server
    error propagates: scoring the repo as bare would cache a wrong, low report.
    """
    owner, name = repo.full_name.split("/", 1)
    entries = await gh.get_repo_root_contents(owner, name)
    names = [entry.name for entry in entries]
    signals = _classify_root_entries(
        names, dir_names=[entry.name for entry in entries if entry.type == "dir"]
    )
    repo.readme_bytes = max(
        (e.size for e in entries if e.type == "file" and e.name.lower().startswith("readme")),
        default=0,
    )
    repo.manifests = _manifests(names)
    repo.has_readme = signals.has_readme
    repo.has_tests = signals.has_tests
    repo.has_ci = signals.has_ci
    for hint in signals.deployment_hints:
        if hint not in repo.deployment_hints:
            repo.deployment_hints.append(hint)
    return signals.workflow_dirs


async def _probe_workflow_files(
    candidates: list[tuple[Repo, tuple[str, ...]]], gh: GitHubClient
) -> dict[str, int]:
    """Ask every candidate repo for its CI workflow files in one GraphQL query.

    A repo has CI when `.github/workflows` (or the Forgejo / Gitea equivalent)
    holds a .yml/.yaml file. Returns full_name -> workflow file count. The probe
    only sharpens the CI signal, so a failed one falls back to the old reading
    (a `.github` directory counts); a rate limit still propagates.
    """
    if not candidates:
        return {}
    variables: dict[str, Any] = {"owner": candidates[0][0].full_name.split("/", 1)[0]}
    variables.update({f"n{i}": repo.name for i, (repo, _dirs) in enumerate(candidates)})
    data: dict[str, Any] = {}
    try:
        data = await gh.graphql(workflow_files_query(len(candidates)), variables) or {}
    except (httpx.HTTPStatusError, httpx.TransportError, RuntimeError):
        logger.warning("Workflow probe failed", exc_info=True)

    counts: dict[str, int] = {}
    for i, (repo, dirs) in enumerate(candidates):
        found = data.get(f"r{i}")
        if found is None:
            repo.has_ci = repo.has_ci or ".github" in dirs
            continue
        count = sum(
            1
            for alias, _path in WORKFLOW_FORGES
            for entry in (found.get(alias) or {}).get("entries") or []
            if entry.get("type") == "blob"
            and str(entry.get("name", "")).lower().endswith(_WORKFLOW_FILE_SUFFIXES)
        )
        if count:
            repo.has_ci = True
            counts[repo.full_name] = count
    return counts


async def _inspect_repo_roots(repos: list[Repo], gh: GitHubClient) -> dict[str, int]:
    """Root-listing signals for each repo, then one probe of the CI workflow
    directories found. Returns the workflow file count per repo."""
    workflow_dirs = await gather_all(*(_enrich_repo_signals(r, gh) for r in repos))
    candidates = [(r, dirs) for r, dirs in zip(repos, workflow_dirs, strict=True) if dirs]
    return await _probe_workflow_files(candidates, gh)


async def _external_pr_signals(username: str, gh: GitHubClient) -> dict[str, Any]:
    """Merged PRs into other people's repositories, account badges and external
    orgs — the cheaper half; GitHub can usually compute this even for very
    active accounts."""
    try:
        external = await gh.graphql(
            EXTERNAL_PRS,
            {"login": username, "externalMerged": external_merged_prs_query(username)},
        )
    except GitHubRateLimited:
        raise
    except Exception:
        logger.warning(
            "External PR/badge signals unavailable for %s; degrading to defaults",
            username,
            exc_info=True,
        )
        return {}
    external_user = external.get("user") or {}
    external_prs = external.get("search") or {}

    external_orgs: set[str] = set()
    for node in external_prs.get("nodes") or []:
        owner_login = ((node or {}).get("repository") or {}).get("owner", {}).get("login")
        if owner_login and owner_login.lower() != username.lower():
            external_orgs.add(owner_login)

    return {
        "has_sponsors_listing": external_user.get("hasSponsorsListing", False),
        "is_github_star": external_user.get("isGitHubStar", False),
        "is_developer_program_member": external_user.get("isDeveloperProgramMember", False),
        "external_prs_merged": external_prs.get("issueCount", 0),
        "external_orgs": external_orgs,
    }


async def _external_review_count(username: str, gh: GitHubClient) -> int:
    """PR review count — isolated because it's the field GitHub most often rejects."""
    try:
        reviews = await gh.graphql(EXTERNAL_REVIEW_COUNT, {"login": username})
    except GitHubRateLimited:
        raise
    except Exception:
        logger.warning(
            "External review-count signal unavailable for %s; degrading to 0",
            username,
            exc_info=True,
        )
        return 0
    review_user = reviews.get("user") or {}
    review_contributions = (review_user.get("contributionsCollection") or {}).get(
        "pullRequestReviewContributions"
    ) or {}
    return review_contributions.get("totalCount", 0)


async def _ingest_external_signals(username: str, gh: GitHubClient) -> dict[str, Any]:
    """Fetch external-contribution signals: merged PRs, review count, badges, orgs.

    Split into two independent GraphQL calls so a failure of one can't sink the
    other. GitHub rejects the review-count field with RESOURCE_LIMITS_EXCEEDED for
    hyper-active accounts (SKILL-ISSUE-BACKEND-4); isolating it keeps the cheaper
    merged-PR / badge signals intact when only that field blows the budget. Every
    field here is a bonus signal, so any failure degrades to a conservative default
    rather than failing the whole analysis.
    """
    pr_signals, external_reviews = await gather_all(
        _external_pr_signals(username, gh), _external_review_count(username, gh)
    )
    return {
        "has_sponsors_listing": False,
        "is_github_star": False,
        "is_developer_program_member": False,
        "external_prs_merged": 0,
        "external_orgs": set(),
        **pr_signals,
        "external_reviews": external_reviews,
    }


async def ingest_profile(username: str, gh: GitHubClient) -> Profile:
    user = await gh.get_user(username)
    # GitHub reuses the /users/{login} endpoint for organisations — same shape,
    # different `type`. Our scoring engine assumes an individual developer
    # (pinned repos, contribution graph, PRs opened, commit cadence). Orgs
    # also break the GraphQL queries since `user(login:)` returns null for
    # an org and downstream `.get(...).get(...)` chains null-deref. Detect
    # early and surface a clean 422 so the caller can render a helpful
    # message instead of a generic 500.
    if user.get("type") == "Organization":
        raise NotAnIndividualError(
            f"'{username}' is a GitHub organization, not a user. "
            "Skill Issue scores individual developers — try a username instead."
        )

    # Everything below needs only the login, so it is issued at once; the
    # client bounds how many requests are actually in flight.
    repos_raw, pinned, external_signals, profile_readme = await gather_all(
        gh.list_repos(username),
        gh.graphql(PINNED_REPOS, {"login": username}),
        _ingest_external_signals(username, gh),
        gh.get_profile_readme(username),
    )

    repos = [_repo_from_rest(r) for r in repos_raw if not r.get("fork", False)]
    pinned_count = ((pinned.get("user") or {}).get("pinnedItems") or {}).get("totalCount") or 0

    # Root contents (README / tests / CI / deployment) and languages for the
    # first ROOT_CONTENT_LIMIT repos, plus two years of commit days from the
    # ten most recently updated (Consistency reads the last year, Learning
    # Trajectory compares it with the one before). All three run together.
    inspected = repos[:ROOT_CONTENT_LIMIT]
    top_repos = [r for r in repos_raw if not r.get("fork")][:10]
    now = datetime.now(UTC)
    one_year_ago = now - timedelta(days=365)
    two_years_ago = now - timedelta(days=730)
    workflow_counts, language_maps, commit_lists = await gather_all(
        _inspect_repo_roots(inspected, gh),
        gather_all(*(gh.list_languages(*r.full_name.split("/", 1)) for r in inspected)),
        gather_all(
            *(
                gh.list_commits(
                    r["owner"]["login"],
                    r["name"],
                    username,
                    two_years_ago.isoformat(),
                    per_page=_COMMITS_PER_REPO,
                )
                for r in top_repos
            )
        ),
    )

    languages: dict[str, int] = {}
    for repo_languages in language_maps:
        for language, bytes_count in repo_languages.items():
            languages[language] = languages.get(language, 0) + bytes_count

    commit_dates_set: set[datetime] = set()
    commit_subjects: list[str] = []
    complete_since: datetime | None = None
    # Repos whose full page fits inside the last year: the year before is unseen.
    cut_within_year: list[dict[str, Any]] = []
    for raw, repo_commits in zip(top_repos, commit_lists, strict=True):
        repo_days: list[datetime] = []
        for c in repo_commits:
            commit = c.get("commit") or {}
            day = _commit_day(commit)
            if day is not None:
                commit_dates_set.add(day)
                repo_days.append(day)
            # Commit messages are untrusted text: keep a bounded first line.
            subject = str(commit.get("message") or "")[:_COMMIT_SUBJECT_MAX].splitlines()
            if subject and subject[0].strip():
                commit_subjects.append(subject[0].strip())
        if len(repo_commits) >= _COMMITS_PER_REPO and repo_days:
            oldest = min(repo_days)
            complete_since = oldest if complete_since is None else max(complete_since, oldest)
            if oldest > one_year_ago:
                cut_within_year.append(raw)

    # Learning Trajectory credits commits in each of the last two years. When
    # the year before is invisible only because pages were cut off inside the
    # last year, ask those repos for one commit from it.
    if cut_within_year and not any(two_years_ago < d <= one_year_ago for d in commit_dates_set):
        older_pages = await gather_all(
            *(
                gh.list_commits(
                    raw["owner"]["login"],
                    raw["name"],
                    username,
                    two_years_ago.isoformat(),
                    per_page=1,
                    until=one_year_ago.isoformat(),
                )
                for raw in cut_within_year
            )
        )
        for page in older_pages:
            for c in page:
                if (day := _commit_day(c.get("commit") or {})) is not None:
                    commit_dates_set.add(day)

    return Profile(
        username=user["login"],
        bio=user.get("bio"),
        profile_readme_chars=_visible_chars(profile_readme),
        pinned_count=pinned_count,
        followers=user.get("followers", 0),
        public_repos=user.get("public_repos", 0),
        languages=languages,
        repos=repos,
        external_prs_merged=external_signals["external_prs_merged"],
        external_reviews=external_signals["external_reviews"],
        external_orgs=external_signals["external_orgs"],
        commit_dates=sorted(commit_dates_set),
        commit_subjects=commit_subjects,
        commit_history_complete_since=complete_since,
        workflow_counts=workflow_counts,
        account_created_at=_parse_dt(user["created_at"]) or datetime.now(UTC),
        company=user.get("company"),
        blog=user.get("blog"),
        hireable=bool(user.get("hireable")),
        has_sponsors_listing=external_signals["has_sponsors_listing"],
        is_github_star=external_signals["is_github_star"],
        is_developer_program_member=external_signals["is_developer_program_member"],
    )
