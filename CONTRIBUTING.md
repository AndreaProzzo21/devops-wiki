
# Contributing

Contributions are welcome! Help us expand DevOps Command Wiki by adding useful commands, improving existing entries, or introducing support for new tools and technologies.

You can contribute by opening a Pull Request against the `main` branch.

## 1. Adding a New Command

Commands are stored in YAML files inside the `data/` directory.

To add a command to an existing tool:

1. Find the YAML file associated with the tool.
2. Add your entry using the structure below.
3. Choose a unique `id`.
4. Follow the existing naming and categorization conventions.

### Command Structure

```yaml
- id: docker-container-prune
  tool: docker
  category: containers
  name: docker container prune
  syntax: docker container prune [OPTIONS]
  summary: Remove all stopped containers
  description: Clean up unused containers to free disk space.
  flags:
    - {flag: "-f, --force", description: "Do not prompt for confirmation"}
    - {flag: "--filter", description: "Filter which containers to remove"}
  examples:
    - {cmd: "docker container prune", description: "Remove all stopped containers"}
    - {cmd: "docker container prune -f", description: "Remove stopped containers without confirmation"}
  keywords: [docker, containers, cleanup, prune, remove]
  related: [docker-ps, docker-rm]
  danger: caution
```

### Field Reference

| Field | Required | Description |
|---|---|---|
| `id` | Yes | Unique identifier, preferably lowercase kebab-case |
| `tool` | Yes | Tool identifier, e.g. `docker`, `ansible`, `kubectl` |
| `category` | Yes | Command category |
| `name` | Yes | Display name |
| `syntax` | Yes | Command syntax and main options |
| `summary` | Yes | Short explanation of the command |
| `description` | No | Additional context or practical details |
| `flags` | No | List of flags and their descriptions |
| `examples` | No | Practical command examples |
| `keywords` | No | Search terms and alternative phrases |
| `related` | No | IDs of related commands |
| `danger` | No | Risk level, when applicable |

For `danger`, follow the conventions used by existing entries. For example, use `caution` when a command can have significant side effects.

## 2. Adding a New Tool

Want to introduce a new technology or DevOps tool?

We welcome contributions for tools such as Terraform, Helm, Prometheus, Git, and many others.

To add a new tool:

1. Create a new YAML file inside `data/`, following the existing file naming conventions.
2. Add commands using the structure described above.
3. Set the same `tool` identifier across all entries belonging to that tool.
4. Use consistent categories to organize its commands.
5. Include a useful initial collection of commands rather than a single isolated entry.

Make sure the new tool follows the existing data conventions and can be correctly discovered by the application.

If your contribution requires changes to the application code, include those changes in the same Pull Request and explain why they are needed.

## 3. Writing Good Entries

A few guidelines help keep the database consistent:

- Use clear, concise summaries.
- Prefer practical examples over purely theoretical descriptions.
- Include useful flags and options.
- Add relevant keywords to improve searchability.
- Use existing categories whenever possible.
- Avoid duplicate commands and IDs.
- Verify syntax and examples against the tool's documentation.
- Keep YAML formatting consistent with existing files.

## 4. Submitting a Pull Request

1. Fork the repository.
2. Create a feature branch.
3. Add or update your YAML entries.
4. Check YAML syntax and consistency.
5. Run the test suite:

   ```bash
   pip install -r requirements.txt
   pip install pytest httpx
   pytest -v tests/
   ```

6. Commit and push your changes.
7. Open a Pull Request against `main`.

In your Pull Request, briefly explain:

- What commands or tools you added.
- Which YAML files you modified.
- Any application changes required.

All contributions will be reviewed before being merged.

Thanks for helping make DevOps Command Wiki a better resource for the DevOps community!
