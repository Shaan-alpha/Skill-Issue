"""Root-listing heuristics: which file and directory names mean tests, CI or a
deployment. Sets follow the 2026-10-13 research (official docs for each tool);
they favour precision, so generic names that collide with unrelated projects
stay out."""

import pytest

from app.ingestion.profile import _classify_root_entries


def _has_tests(*entries: str) -> bool:
    return _classify_root_entries(list(entries))[1]


def _has_ci(*entries: str) -> bool:
    return _classify_root_entries(list(entries))[2]


def _deploy(*entries: str) -> list[str]:
    return _classify_root_entries(list(entries))[3]


@pytest.mark.parametrize(
    "entry",
    [
        "tests",
        "test",
        "__tests__",
        "spec",
        "e2e",
        "cypress",
        "integration_test",
        "t",
        "testdata",
        "MyApp.Tests",
        "Core.Test",
        "vitest.config.ts",
        "vitest.config.mts",
        "vitest.unit.config.ts",
        "vitest.workspace.ts",
        "jest.config.js",
        "jest.config.json",
        "playwright.config.ts",
        "cypress.config.mjs",
        "cypress.json",
        "karma.conf.js",
        ".mocharc.yml",
        "pytest.ini",
        ".pytest.ini",
        "pytest.toml",
        "conftest.py",
        "tox.ini",
        "noxfile.py",
        "phpunit.xml",
        "phpunit.xml.dist",
        ".rspec",
        "dart_test.yaml",
        "main_test.go",
    ],
)
def test_recognises_a_test_suite(entry: str) -> None:
    assert _has_tests(entry)


@pytest.mark.parametrize(
    "entry",
    ["specs", "vite.config.ts", "testing", "latest", "contest.md", "src", "README.md"],
)
def test_does_not_mistake_these_for_a_test_suite(entry: str) -> None:
    assert not _has_tests(entry)


@pytest.mark.parametrize(
    "entry",
    [
        ".gitlab-ci.yml",
        ".circleci",
        "Jenkinsfile",
        ".travis.yml",
        "azure-pipelines.yml",
        ".azure-pipelines.yml",
        "bitbucket-pipelines.yml",
        ".drone.yml",
        ".woodpecker.yml",
        ".woodpecker.yaml",
        ".woodpecker",
        ".buildkite",
        "buildkite.yml",
        "appveyor.yml",
        ".appveyor.yml",
        ".semaphore",
        "codemagic.yaml",
        "bitrise.yml",
        "cloudbuild.yaml",
        "buildspec.yml",
        ".tekton",
        ".teamcity",
    ],
)
def test_recognises_a_ci_config(entry: str) -> None:
    assert _has_ci(entry)


@pytest.mark.parametrize(
    "entry",
    [
        # Only their workflows/ subdirectory runs CI; the listing alone can't tell.
        ".github",
        ".forgejo",
        ".gitea",
        # Cirrus CI shut down on 2026-06-01; Earthly is unmaintained; Dagger is
        # started from some other CI.
        ".cirrus.yml",
        "Earthfile",
        "dagger.json",
    ],
)
def test_these_alone_do_not_mean_ci(entry: str) -> None:
    assert not _has_ci(entry)


@pytest.mark.parametrize(
    ("entry", "hint"),
    [
        ("Dockerfile", "dockerfile"),
        ("Containerfile", "containerfile"),
        ("compose.yaml", "docker-compose"),
        ("compose.yml", "docker-compose"),
        ("docker-compose.yml", "docker-compose"),
        ("vercel.json", "vercel"),
        ("vercel.ts", "vercel"),
        ("vercel.toml", "vercel"),
        ("netlify.toml", "netlify"),
        ("fly.toml", "fly"),
        ("render.yaml", "render"),
        ("railway.json", "railway"),
        ("railway.toml", "railway"),
        (".railway", "railway"),
        ("wrangler.toml", "cloudflare"),
        ("wrangler.jsonc", "cloudflare"),
        ("wrangler.json", "cloudflare"),
        ("Procfile", "heroku"),
        ("heroku.yml", "heroku"),
        ("serverless.yml", "serverless"),
        ("serverless.ts", "serverless"),
        ("sst.config.ts", "sst"),
        ("amplify.yml", "amplify"),
        ("firebase.json", "firebase"),
        ("samconfig.toml", "aws-sam"),
        ("cdk.json", "aws-cdk"),
        ("appspec.yml", "aws-codedeploy"),
        (".ebextensions", "elastic-beanstalk"),
        ("Pulumi.yaml", "pulumi"),
        ("main.tf", "terraform"),
        ("network.tf", "terraform"),
        (".terraform.lock.hcl", "terraform"),
        ("Chart.yaml", "helm"),
        ("helmfile.yaml", "helmfile"),
        ("kustomization.yaml", "kustomize"),
        ("skaffold.yaml", "skaffold"),
        (".do", "digitalocean"),
        ("zbpack.json", "zeabur"),
        ("captain-definition", "caprover"),
        (".kamal", "kamal"),
        ("railpack.json", "railpack"),
        ("nixpacks.toml", "nixpacks"),
        ("app.yaml", "app-engine"),
    ],
)
def test_recognises_a_deployment_config(entry: str, hint: str) -> None:
    assert hint in _deploy(entry)


@pytest.mark.parametrize(
    "entry",
    # app.json is also Expo's app config, template.yaml is generic, now.json
    # stopped working on 2026-03-31, and these directories are naming habits.
    ["app.json", "template.yaml", "now.json", "charts", "deploy", "infra", "k8s"],
)
def test_does_not_mistake_these_for_deployment(entry: str) -> None:
    assert _deploy(entry) == []


def test_two_spellings_of_one_tool_are_one_hint() -> None:
    assert _deploy("compose.yaml", "docker-compose.yml", "Dockerfile") == [
        "dockerfile",
        "docker-compose",
    ]
