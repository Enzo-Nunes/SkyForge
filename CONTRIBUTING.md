# Contributing to SkyForge

Thank you for your interest in contributing to SkyForge! This guide explains how to report issues, suggest features, and submit pull requests.

---

## Getting Started

### Local Development Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/Enzo-Nunes/SkyForge.git
   cd SkyForge
   git checkout dev
   ```

2. **Install pre-commit hooks** (auto-formats & lints before commit):

   ```bash
   pip install pre-commit
   pre-commit install
   ```

   This installs:
   - **Ruff** — Python linting and formatting.
   - **Prettier** — Vue, JavaScript, JSON, YAML formatting.

   These runs automatically on `git commit`.

3. **Start the development stack:**

   ```bash
   docker compose up --build -d
   ```

4. **Access the UI:**
   - Open <http://localhost:8000> in your browser
   - Changes to Vue components are reflected after page refresh

5. **Make changes and rebuild as required:**

    ```bash
    docker compose up --build -d <service-name>
    ```

6. **View Logs:**

    ```bash
    docker compose logs -f          # View all services
    docker compose logs -f db-api   # View specific service (e.g., db-api, calculator, scraper, web)
    ```

---

## Branch Strategy

- **`main`** — Stable, production-ready releases. Protected branch.
- **`dev`** — Integration branch for community contributions. Base branch for pull requests.

**How it works:**

1. Create a feature branch from `dev`: `git checkout -b feature/my-feature dev`
2. Make your changes and test locally
3. Submit a Pull Request against `dev` (not `main`)
4. After review and merge to `dev`, changes go to `main` on the next release

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

#### Code Style

- **Python:** Follow PEP 8. Use type hints where possible.
- **Vue/JavaScript:** Use the existing component structure. Prefer `<script setup>` composition API.
- **SQL:** Parameterized queries only (never string concatenation). Comments for complex logic.

#### Before Submitting

1. **Test locally:**

   ```bash
   docker compose down -v  # Clean slate
   docker compose up --build
   ```

2. **Check for obvious issues:**
   - No hardcoded secrets or credentials
   - No `console.log()` or `print()` debug statements left in
   - Database migrations (if schema changes) documented in the PR

3. **Update documentation:**
   - If your change affects usage or configuration, update `README.md` or add docs as needed.

4. **Clean up your commit history:**

   ```bash
   git rebase -i dev  # Squash WIP commits into logical changes
   ```

#### Creating a Pull Request

1. **Push your feature branch:**

   ```bash
   git push origin feature/my-feature
   ```

2. **Open PR on GitHub:**
   - Base branch: `dev`
   - Title: Clear, descriptive (e.g., "Add email notifications for low profit items")
   - Description:

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

3. **Address review feedback:**
   - Push new commits to the same branch
   - Respond to comments with clarifications
   - Request re-review when done

---

## Licensing

By contributing, you agree that your contributions will be licensed under the same license as the project (GPL v3). See [LICENSE](LICENSE) for details.

---

## Thank You

I appreciate your effort to make SkyForge better. Whether it's a bug report, feature request, or code contribution, your input helps the community. 🙏
