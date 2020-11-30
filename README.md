# Time Series Mosaicker for Sentinel-1 and 2 

This program will, for any given area of interest (AOI), download and create sentinel-1 and 2 mosaics for one or many time intervals.

It will make sure to download the absolute minimum data necessary to form the mosaics!

## Flowchart

![Flowchart](https://github.com/Thetaspace/TS_Sen12Mosaicker/blob/master/ts_mosaicker.png?raw=true)

## Absolute Minimum Data to Download


## Installation

Clone the repository to your local.

```bash
git clone https://github.com/Thetaspace/TS_Sen12Mosaicker.git
```
and install the requirements
```bash
pip install -r requirements.txt
```
or (recommended) just use the Dockerfile to build the docker image with everything you need.
```bash
docker build --tag sen12mosaicker
```

## Usage

1. Please fill the configuration file (config.yaml) with your meta data of choice (e.g. cloud cover, time interval, ... )

2. Open Access Hub credentials are required. Please fill in the json file (OAH_creds.json) you may rename it but make sure to change config.yaml accordingly.

3. Choose your Area of Interest and as a geosjon string in a file (map.geojson). You may rename it but make sure to change config.yaml accordingly.

For the fully automatic processing run the main.py

```bash
python main.py
```


## Contributing
Bug? open a new issue! You have a question or a suggestion? reach us! Even better:
create a Pull request! For major changes, please open an issue first to discuss what you would like to change.

## License
[MIT](https://choosealicense.com/licenses/mit/)
