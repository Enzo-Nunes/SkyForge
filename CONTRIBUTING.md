# Contributing to SkyForge

Thank you for your interest in contributing to SkyForge! This guide explains how to report issues, suggest features, and submit pull requests.

---

## Getting Started

### Local Development Setup

1. **Fork the repository:**
   - Click the **Fork** button on GitHub (top-right)
   - This creates your personal copy of the repository

2. **Clone your fork:**

   ```bash
   git clone https://github.com/YOUR-USERNAME/SkyForge.git
   cd SkyForge
   git checkout dev
   ```

3. **Install pre-commit hooks** (auto-formats & lints before commit):

   ```bash
   pip install pre-commit
   pre-commit install
   ```

   This installs:
   - **Ruff** — Python linting and formatting.
   - **Prettier** — Vue, JavaScript, JSON, YAML formatting.

   These run automatically on `git commit`.

4. **Start the development stack:**

   ```bash
   docker compose up --build -d
   ```

5. **Access the UI:**
   - Open <http://localhost:8145> in your browser
   - Changes to Vue components are reflected after page refresh

6. **Make changes and rebuild as required:**

    ```bash
    docker compose up --build -d <service-name>
    ```

7. **View Logs:**

    ```bash
    docker compose logs -f          # View all services
    docker compose logs -f db-api   # View specific service (e.g., db-api, calculator, scraper, web)
    ```

---

## Types of Contributions

### Report a Bug

1. Go to **Issues** → **New Issue**
2. Use the **Bug Report** template
3. Include:
   - Description of the bug
   - Steps to reproduce
   - Expected vs. actual behavior
   - OS/browser and SkyForge uptime (if relevant)
   - Logs from `docker compose logs`

### Request a Feature

1. Go to **Issues** → **New Issue**
2. Use the **Feature Request** template
3. Describe:
   - What you want to add
   - Why it's useful
   - Any design thoughts or mockups

### Submit a Pull Request

#### Branch Strategy

- **`main`** — Stable, production-ready releases. Protected branch.
- **`dev`** — Integration branch for community contributions. **Always submit PRs against `dev`, not `main`.**

#### Before Submitting

1. **Create a feature branch from `dev`:**

   ```bash
   git checkout -b feature/my-feature dev
   ```

2. **Test locally:**

   ```bash
   docker compose down -v  # Clean slate
   docker compose up --build
   ```

3. **Check for obvious issues:**
   - No hardcoded secrets or credentials
   - No `console.log()` or `print()` debug statements left in
   - Database migrations (if schema changes) documented in the PR

4. **Update documentation:**
   - If your change affects usage or configuration, update `README.md` or add docs as needed.

#### Submitting Your PR

1. **Push your feature branch to your fork:**

   ```bash
   git push origin feature/my-feature
   ```

2. **Open a Pull Request on GitHub:**
   - Go to the **original SkyForge repository**
   - Click **"Pull Requests"** → **"New Pull Request"**
   - Click **"compare across forks"**
   - Set:
     - **Base repository:** `Enzo-Nunes/SkyForge`
     - **Base branch:** `dev`
     - **Head repository:** `YOUR-USERNAME/SkyForge`
     - **Head branch:** `feature/my-feature`

3. **Fill in the PR description:**
   - **Title:** Clear, descriptive (e.g., "Add email notifications for low profit items")
   - **Description** (use this template):

     ```plaintext
     ## What
     Adds email notifications when profit drops below a threshold
     
     ## Why
     Users can react faster to market changes
     
     ## How
     - New `notification_service` module
     - Settings UI with email and threshold config
     - Sends email on calculation cycle if condition met
     
     ## Testing
     - Tested with mock SMTP server
     - Verified email triggers correctly
     - No regressions in existing features
     
     Closes #123
     ```

4. **Address review feedback:**
   - Push new commits to the same branch
   - Respond to comments with clarifications
   - Request re-review when done

---

## Licensing

By contributing, you agree that your contributions will be licensed under the same license as the project (GPL v3). See [LICENSE](LICENSE) for details.

---

## Thank You

I appreciate your effort to make SkyForge better. Whether it's a bug report, feature request, or code contribution, your input helps the community. 🙏
