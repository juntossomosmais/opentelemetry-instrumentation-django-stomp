# Contributing to `opentelemetry-instrumentation-django-stomp`

This repository uses [trunk based development](https://github.com/cgbystrom/awesome-trunk-based-dev). The picture below depicts what you must follow to properly contribute to this project:

![git-workflow](./docs/git-workflow.png?raw=true)

Follow the steps below if you want to contribute with `opentelemetry-instrumentation-django-stomp`:

- Firstly, you should search in [issues](https://github.com/juntossomosmais/opentelemetry-instrumentation-django-stomp/issues) something that you want to work with. You could filter those with `help wanted` (Good for community contributors to help, up-for-grabs) or `good first issue` labels. If you don't find issue with your contribution idea you can create one issue or open a [discussion](https://github.com/juntossomosmais/opentelemetry-instrumentation-django-stomp/discussions) to explain your idea or requirement for contribution;
- To contribute, you must create a new branch for `main` from this repo;
- Then, you must create the code following the [Code style](#code-style) and push them in your branch created previously;
- After all commits, you should open a PR from your branch to the `main` branch;
  - The PR go trigger a pipeline with test, sonar and lint validation, if all checks are OK a test version package is generate and published in https://test.pypi.org/project/opentelemetry-instrumentation-django-stomp/;
  - The Maintainers will use this package to validate the incoming code; 
- Maintainers will review your pull request ASAP, and they can approve it or request updates;
- Maintainers will merge the PR and a new version of package will be generated;

## Contributing with issues or discussions

Another way to contribute is creating an [issues](https://github.com/juntossomosmais/opentelemetry-instrumentation-django-stomp/issues) or [discussion](https://github.com/juntossomosmais/opentelemetry-instrumentation-django-stomp/discussion). Feel free to write as many issues as you want, they are very important to help us to launch new releases and solving bugs. It's recommended to label you issue with any one of the following labels: `question`, `bug` or `enhancement`.

# Code style

### Test

Make sure to run all the tests before opening a pull request. Any new feature should also be tested!. You can run the tests with docker or tox

```shell
docker-compose up integration-tests
```

Or using `tox`

```shell
pipenv run tox
```

### Lint + code formatter
The project use `.pre-commit-config.yaml` of [flake8](https://github.com/pycqa/flake8), [black](https://black.readthedocs.io/en/stable/), [isort](https://pycqa.github.io/isort/) and [pylint](https://pylint.org/).You can run the `.pre-commit-config.yaml` with docker

```shell
docker-compose up lint-formatter
```

Or using `pre-commit`

```shell
pre-commit run --all-files
```

### Sonar

The pull request will run sonar which may show some flags and these should be resolved. Is expected 90% of coverage in new codes.

### Commits

The `commit` summary should be structured as [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/) standard.
