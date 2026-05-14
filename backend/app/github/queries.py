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
