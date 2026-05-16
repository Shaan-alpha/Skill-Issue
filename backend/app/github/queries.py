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
