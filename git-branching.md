
## Step-by-Step Guide to Git Branching, Tagging, and Releases

### 1. **Create a New Repository on GitHub**

1. **Sign In**: Log in to your GitHub account.

2. **Create Repository**:
   - Click the "+" icon in the upper-right corner of GitHub and select "New repository."
   - Alternatively, visit [github.com/new](https://github.com/new).

3. **Fill in Repository Details**:
   - **Repository Name**: Enter a name for your repository, e.g., `my-project`.
   - **Description**: (Optional) Provide a brief description, e.g., "A sample project to demonstrate Git workflows."
   - **Public/Private**: Choose whether to make your repository public or private.
   - **Initialize with a README**: Check this box to include a README file.
   - **.gitignore**: Optionally, choose a .gitignore template for your project.
   - **License**: Optionally, select a license for your project.

4. **Create Repository**: Click the "Create repository" button.

---

### 2. **Clone the Repository Locally**

1. **Clone URL**: On your repository page, click the "Code" button to copy the URL for cloning (HTTPS or SSH).

2. **Clone Command**:
   Open your terminal and run:
   ```bash
   git clone <repository-url>
   ```
   Replace `<repository-url>` with the URL you copied.

3. **Navigate to Directory**:
   ```bash
   cd my-project
   ```

---

### 3. **Set Up Branches According to the Workflow**

#### Create and Push `develop` Branch

1. **Create `develop` (from `main`) Branch**:
   ```bash
   git checkout -b develop 
   ```

2. **Push `develop` Branch**:
   ```bash
   git push origin develop
   ```

#### Create and Push Feature Branches

1. **Create a Feature Branch (from `develop`) **:
   ```bash
   git checkout -b feature/new-feature 
   ```

2. **Work on Your Feature**:
   - Make changes and commit them:
   ```bash
   # Make your changes
   git add .
   git commit -m "Add new feature"
   ```

3. **Push Feature Branch**:
   ```bash
   git push origin feature/new-feature
   ```

#### Create and Push Release Branches

1. **Create a Release Branch (from `develop`)**:
   ```bash
   git checkout -b release/1.0.0 
   ```

2. **Prepare for Release**:
   - Make release-related changes, then commit them:
   ```bash
   git add .
   git commit -m "Prepare for release 1.0.0"
   ```

3. **Push Release Branch**:
   ```bash
   git push origin release/1.0.0
   ```

#### Create and Push Hotfix Branches

1. **Create a Hotfix Branch (from `main`)**:
   ```bash
   git checkout -b hotfix/1.0.1 
   ```

2. **Apply Hotfix**:
   - Make changes and commit them:
   ```bash
   git add .
   git commit -m "Fix critical issue in 1.0.0"
   ```

3. **Push Hotfix Branch**:
   ```bash
   git push origin hotfix/1.0.1
   ```

---

### 4. **Merge Branches**

#### Merge Feature Branch into `develop`

1. **Merge Feature Branch**:
   ```bash
   git checkout develop
   git pull origin develop
   git merge feature/new-feature
   git push origin develop
   ```

#### Merge Release Branch into `main` and `develop`

1. **Merge Release Branch into `main`**:
   ```bash
   git checkout main
   git pull origin main
   git merge release/1.0.0
   git tag -a v1.0.0 -m "Release version 1.0.0"
   git push origin main --tags
   ```

2. **Merge Release Branch into `develop`**:
   ```bash
   git checkout develop
   git pull origin develop
   git merge release/1.0.0
   git push origin develop
   ```

#### Merge Hotfix Branch into `main` and `develop`

1. **Merge Hotfix Branch into `main`**:
   ```bash
   git checkout main
   git pull origin main
   git merge hotfix/1.0.1
   git tag -a v1.0.1 -m "Hotfix version 1.0.1"
   git push origin main --tags
   ```

2. **Merge Hotfix Branch into `develop`**:
   ```bash
   git checkout develop
   git pull origin develop
   git merge hotfix/1.0.1
   git push origin develop
   ```

---

### 5. **Create Releases on GitHub**

1. **Navigate to Releases**:
   Go to your repository on GitHub and click on the “Releases” tab.

2. **Draft a New Release**:
   Click “Draft a new release.”

3. **Select a Tag**:
   - Choose an existing tag or create a new tag. For example, select `v1.0.0` or `v1.0.1`.

4. **Fill in Details**:
   - **Release Title**: e.g., "Release version 1.0.0".
   - **Description**: Write a summary of what’s new in this release.
   - **Attach Binaries/Assets**: Optionally, upload any files related to the release.

5. **Publish Release**:
   Click “Publish release” to make it visible on the releases page.

---

### Summary

- **Create a Repository**: Set up a new repo on GitHub.
- **Clone and Branch**: Clone the repo, then create and manage branches (`develop`, `feature`, `release`, `hotfix`).
- **Merge**: Merge branches as necessary.
- **Tag and Release**: Create tags for versions, then create releases on GitHub.
