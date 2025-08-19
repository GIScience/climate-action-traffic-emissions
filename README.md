# <img src="resources/icon.jpeg" width="5%"> Traffic Emissions

This plugin estimates daily traffic volume and annual traffic emissions per road segment using the OSM road network, road attributes such as road type, number of lanes, and speed limit from OSM, population density, traffic counts from Berlin, Germany, and emission factors.

## Development setup

To run your plugin locally requires the following setup:

1. Set up the [infrastructure](https://gitlab.heigit.org/climate-action/infrastructure) locally in `devel` mode
2. Copy your [.env.base_template](.env.base_template) to `.env.base` and update it
3. Run `poetry run python {traffic-emissions}/plugin.py`

### Testing

We use [pytest](https://pytest.org) as a testing engine.
Ensure all tests are passing by running `poetry run pytest`.

#### Coverage

To get a coverage report of how much of your code is run during testing, execute
`poetry run pytest --ignore test/core/ --cov`.
We ignore the `test/core/` folder when assessing coverage because the core tests run the whole plugin to be sure
everything successfully runs with a very basic configuration.
Yet, they don't actually test functionality and therefore artificially inflate the test coverage results.

To get a more detailed report including which lines in each file are **not** tested,
run `poetry run pytest --ignore test/core/ --cov --cov-report term-missing`

## Releasing a new plugin version

To release a new plugin version

1. Update the [CHANGELOG.md](CHANGELOG.md).
   It should already be up to date but give it one last read and update the heading above this upcoming release
2. Decide on the new version number.
   Once your plugin outgrew the 'special versions' `dummy` and `mvp`, we suggest you adhere to
   the [Semantic Versioning](https://semver.org/) scheme,
   based on the changes since the last release.
   You can think of your plugin methods (info method, input parameters and artifacts) as the public API of your plugin.
3. Update the version attribute in the [pyproject.toml](pyproject.toml) (e.g. by running
   `poetry version {patch|minor|major}`)
4. Create a [release](https://docs.gitlab.com/ee/user/project/releases/#create-a-release-in-the-releases-page) on
   GitLab, including a changelog
5. Create a MR in the [infrastructure](https://gitlab.heigit.org/climate-action/dev-ops/infrastructure/-/blob/main/doc/Add_Service.md) repository to activate your plugin in production

## Docker

To build docker images, you need to give the engine access to the climatoology repository.
Create a file `CI_JOB_TOKEN` that contains your personal access token to the climatoology repository.

### Build

The tool is also [Dockerised](Dockerfile).
Images are automatically built and deployed in the [CI-pipeline](.gitlab-ci.yml).

In case you want to manually build and run locally (e.g. to test a new feature in development), execute

```shell
docker build --secret id=CI_JOB_TOKEN . --tag repo.heigit.org/climate-action/traffic-emissions:devel
```

Note that this will overwrite any existing image with the same tag (i.e. the one you previously pulled from the Climate
Action docker registry).

To mimic the build behaviour of the CI you have to add `--build-arg CI_COMMIT_SHORT_SHA=$(git rev-parse --short HEAD)`
to the above command.

### Run

If you have the Climate Infrastructure running (see [Development Setup](#development-setup)) you can now run the
container via

```shell
docker run --rm --network=host --env-file .env.base --env-file .env repo.heigit.org/climate-action/traffic-emissions:devel
```

### Deploy

Deployment is handled by the GitLab CI automatically.
If for any reason you want to deploy manually (and have the required rights), after building the image, run

```shell
docker image push repo.heigit.org/climate-action/traffic-emissions:devel
```
