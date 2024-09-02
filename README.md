# Plant Dashboard


## Requirements

### System requirements
The _Plant Dashboard_ require `graphviz` to generates a tasks dependency graph figure.

#### Debian & Ubuntu
On Debian and Ubuntu, you may install the system library with:
```shell
sudo apt-get install graphviz graphviz-dev
```

#### MacOS
On macOS, you may install the system library using the Homebrew package manager as follows:
```shell
brew install graphviz
```

### Conda environment & Python packages
To install the source, let's first create a conda environment:
```shell
conda create -n plant_dashboard python=3.9
conda activate plant_dashboard
```

The _Plant Dashboard_ require some additional Python packages, you may install them with `pip` as follows:
```shell
python -m pip install -e .
```

### ROMI libraries sources
As the _Plant Dashboard_ project is **still under development**, it requires to install the following ROMI libraries from the sources:
 - [romitask](https://github.com/romi/romitask)
 - [plantdb](https://github.com/romi/plantdb)
 - [romicgal](https://github.com/romi/romicgal)
 - [romiseg](https://github.com/romi/romiseg)
 - [plant3dvision](https://github.com/romi/plant3dvisionv)

You can install them all at once with the `plant-3d-vision` sources that list the other ones as submodules:
```shell
# - Clone the sources from the GitHub repository:
git clone https://github.com/romi/plant-3d-vision.git
# - Move to the source directory and initialize the submodules:
cd plant-3d-vision/
git submodule init
git submodule update
# - Install the `plant-3d-vision` & submodule dependencies and sources:
# -- `plantdb` dependencies and sources:
python3 -m pip install --user plantdb/
# -- `romitask` dependencies and sources:
python3 -m pip install --user romitask/
# -- `romiseg` dependencies and sources:
python3 -m pip install --user torch==1.12.1+cu102 torchvision==0.13.1+cu102 --extra-index-url https://download.pytorch.org/whl/cu102 && \
python3 -m pip install --user romiseg/
# -- `romicgal` dependencies and sources:
python3 -m pip install --user pybind11
python3 -m pip install --user romicgal/
# -- `plant-3d-vision` dependencies and sources:
python3 -m pip install --user -r requirements.txt
python3 -m pip install --user .
# -- Clean pip cache:
python3 -m pip cache purge
```


## Getting started

### PlantDB
First we have to start a (test) REST API serving an FSDB database.
It can be done as follows:
```shell
fsdb_rest_api --test
```
Note that the `--test` option will create a test database by cloning dataset from Zenodo in `/tmp/ROMI_DB`.
To use an existing database, export the path to the `$ROMI_DB` environment variable or use the `-db` option with a path.

[localhost:5000](http://localhost:5000).

### Luigi central scheduler
You may create a Luigi central scheduler (`luigid` server deamon) as follows: 
```shell
mkdir /tmp/luigi_log
luigid  --logdir /tmp/luigi_log
```
Then you can access luigi WebUI under [localhost:8082](http://localhost:8082).

If you do not do this, you need to call the `luigi` CLI with the `--local-scheduler` argument.

See [Using the Central Scheduler](https://luigi.readthedocs.io/en/stable/central_scheduler.html) for more details. 

### Redis
We use a docker container to provide a `Redis` _broker_ and _backend_ to `Celery`.

Start a redis container named `plant-dashboard-redis`, in background mode and binding port `6379` from host to `6379` in container:
```shell
docker run --name plant-dashboard-redis --rm -p 6379:6379 redis
```
You may want to use the `-d` option to detach the process and let it run in the background.

To get the IP address of the running container "plant-dashboard-redis", use:
```shell
docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' plant-dashboard-redis
```

Use this in the `Celery` app configuration or in `celeryconfig.py`, _e.g._ with `172.17.0.2` as IP:
```python
celery_app = Celery(__name__,
                    broker="redis://172.17.0.2:6379/0",
                    backend="redis://172.17.0.2:6379/1",
                    # ...
                    )
```

### Celery
We now have to create a `celery` worker to receive the long callbacks (like reconstruction pipelines) from the WebUI.
From the `plant-dashboard` root directory, it can be started as follows:
```shell
cd plant_dashboard/webui
celery -A app:celery_app worker --loglevel=INFO
```

### Flower
To access Celery tasks & worker statuses we use `flower` to get an API that serve such information.
From the `plant-dashboard` root directory, it can be started as follows:
```shell
cd plant_dashboard/webui
celery -A app:celery_app flower --port=5555 --basic-auth=${FLOWER_USER}:${FLOWER_PWD}
```
The flower web-interface should be accessible under [0.0.0.0:5555](http://0.0.0.0:5555).
Do not forget to define `${FLOWER_USER}` & `${FLOWER_PWD}` as environment variables.

### WebUI
Finally, you can start the Dash WebUI.
From the `plant-dashboard` root directory, it can be started as follows:
```shell
cd plant_dashboard/webui/
python app.py
```
Our web-interface should be accessible under [localhost:3000](http://localhost:3000).

We have to start our Dash App in this folder, so it knows where the `pages` directory is.

## Sources and documentation

- [Dash](https://dash.plotly.com/)
- [Dash-Bootstrap-Components](https://dash-bootstrap-components.opensource.faculty.ai/docs/components/)
- [Bootstrap-Icons](https://icons.getbootstrap.com/)
- [Luigi](https://luigi.readthedocs.io/en/stable/index.html)
- [Celery](https://docs.celeryq.dev/en/stable/index.html)
