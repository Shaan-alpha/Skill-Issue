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

EXTERNAL_PRS = """
query ExternalPRs($login: String!) {
  user(login: $login) {
    hasSponsorsListing
    isGitHubStar
    isDeveloperProgramMember
    pullRequests(states: MERGED, first: 100) {
      totalCount
      nodes {
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
query($login: String!) {
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
query($login: String!, $from: DateTime!, $to: DateTime!) {
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
