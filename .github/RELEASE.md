# Release Process

This document provides a comprehensive guide on the steps to execute a release for this project.

## Prerequisites

Before initiating the release process, ensure the following prerequisites are met:

- Commit messages must adhere to the [conventional commit specification](https://www.conventionalcommits.org/).
- Proper permissions are in place to create and manage releases.

## Steps

### 1. Create Release

1. **Merge Pull Request to appropriate branch:**
    - Ensure that the changes intended for release are encapsulated in a Pull Request.
    - Merge the approved Pull Request into the `main`. Currently, 
   only the `main` branch is allowed for releasing.

2. **Manual execution of [Release](workflows/release.yml) Action:**
    - The `Release` GitHub Action automates versioning based on conventional commit messages. Pipeline creates tag, release, 
   and pushes new commit in which updates `CHANGELOG.md` and version in `pyproject.toml`.
    - Click on the `Run workflow` button and select the desired branch or run the following command: 
   `gh workflow run --ref <branch|tag> release.yml`.

### 2. Publish Release

1. Releases on GitHub are automatically uploaded (it requires some time to registry index the release).