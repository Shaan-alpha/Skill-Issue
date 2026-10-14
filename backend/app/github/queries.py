# Only the count is scored (Recruiter Signal's ">= 3 pinned repos").
PINNED_REPOS = """
query PinnedRepos($login: String!) {
  user(login: $login) {
    pinnedItems(first: 6, types: [REPOSITORY]) { totalCount }
  }
}
"""

# `user.pullRequests(states: MERGED)` counts every merged PR the user authored,
# their own repositories included, so it cannot answer "how much do you ship
# into other people's code?". The search below excludes repositories the user
# owns (`-user:`); `$externalMerged` is built by external_merged_prs_query().
EXTERNAL_PRS = """
query ExternalPRs($login: String!, $externalMerged: String!) {
  user(login: $login) {
    hasSponsorsListing
    isGitHubStar
    isDeveloperProgramMember
  }
  search(query: $externalMerged, type: ISSUE, first: 100) {
    issueCount
    nodes {
      ... on PullRequest {
        repository {
          owner {
            login
          }
        }
      }
    }
  }
}
"""


def external_merged_prs_query(login: str) -> str:
    """Search string for merged PRs `login` authored in public repositories it
    doesn't own, newest first (the nodes feed the org-diversity signal).

    `is:public` keeps the count independent of the token: search also returns
    private PRs the token can see, and the report cache is keyed by username.
    """
    return f"author:{login} is:pr is:merged is:public -user:{login} sort:updated-desc"


# (alias, directory) for each forge whose Actions-style CI reads <dir>/workflows.
WORKFLOW_FORGES = (("github", ".github"), ("forgejo", ".forgejo"), ("gitea", ".gitea"))


def workflow_files_query(repo_count: int) -> str:
    """One query asking `repo_count` repositories for the files in their CI
    workflow directories. Repositories are aliased r0..rN; their names travel
    as variables $n0..$nN (never interpolated) and all belong to $owner."""
    trees = " ".join(
        f'{alias}: object(expression: "HEAD:{path}/workflows") '
        "{ ... on Tree { entries { name type } } }"
        for alias, path in WORKFLOW_FORGES
    )
    params = "".join(f", $n{i}: String!" for i in range(repo_count))
    repos = " ".join(
        f"r{i}: repository(owner: $owner, name: $n{i}) {{ {trees} }}" for i in range(repo_count)
    )
    return f"query WorkflowFiles($owner: String!{params}) {{ {repos} }}"


# Isolated from EXTERNAL_PRS on purpose: pullRequestReviewContributions.totalCount
# is the field GitHub most often rejects with RESOURCE_LIMITS_EXCEEDED for
# hyper-active accounts (SKILL-ISSUE-BACKEND-4). Keeping it in its own query means
# a rejection here can't take down the merged-PR count / account badges alongside it.
EXTERNAL_REVIEW_COUNT = """
query ExternalReviewCount($login: String!) {
  user(login: $login) {
    contributionsCollection {
      pullRequestReviewContributions(first: 1) {
        totalCount
      }
    }
  }
}
"""

REVIEW_DEPTH = """
query ReviewDepth($login: String!) {
  user(login: $login) {
    contributionsCollection {
      pullRequestReviewContributions(first: 25) {
        nodes { pullRequestReview { bodyText } }
      }
    }
  }
}
"""

CONTRIBUTION_REPOS = """
query ContributionRepos($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      commitContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner }
        contributions { totalCount }
      }
    }
  }
}
"""
