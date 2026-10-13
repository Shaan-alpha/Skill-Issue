PINNED_REPOS = """
query PinnedRepos($login: String!) {
  user(login: $login) {
    pinnedItems(first: 6, types: [REPOSITORY]) {
      nodes {
        ... on Repository {
          name
          nameWithOwner
          stargazerCount
          forkCount
          primaryLanguage { name }
          pushedAt
          createdAt
          isFork
          object(expression: "HEAD:README.md") { ... on Blob { byteSize } }
        }
      }
    }
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
