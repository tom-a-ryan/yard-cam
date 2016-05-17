# yard_cam

# Project Title

Raspberry Pi(s) upload interesting photos to a GAE hosted web-site

## Getting Started

These instructions will get a copy of the project installed on your local machine for development and testing purposes.
The GAE code is loaded to Google's Cloud, the Raspberyr Pi code is downloaded to the Pi dynamically through the GAE web-app.

### Prerequisities

Google Cloud Compute
  - Google App Engine account
  - Google App Engine project
  
Local development machine
  - Google Cloud Compute tools
  - Google Cloudstorage library

Raspberry Pi with camera module
  - standard software
  - virtualenv
  - opencv

### Installing

Google Cloud Compute


Install tools by following instrcutions at

```
https://cloud.google.com/appengine/downloads

```
Navigae to the console to create <your-project>

pip install GoogleAppEngineCloudStorageClient -t <your_app_directory/lib>


follow directions in requirements.text

On raspberry pi:
install opencv
workon cv
...
```

Google App Engine Account and a project_id
  - At present, at hobby/home leve volumes, this does not need to be a paid account
  - google cloud command-line tools installed
  - cloudstorage module must be installed separately

```

```
Give the example
```

And repeat

```
until finished
```

End with an example of getting some data out of the system or using it for a little demo

## Running the tests

Explain how to run the automated tests for this system

### Break down into end to end tests

Upload a new version to GAE
```
appcfg.py -A project_id -V v1 update gae/
```

### And coding style tests

Explain what these tests test and why

```
Give an example
```

## Deployment

Add additional notes about how to deploy this on a live system

## Built With

* Dropwizard - Bla bla bla
* Maven - Maybe
* Atom - ergaerga

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests to us.

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/your/project/tags). 

## Authors

* **Thomas Ryan** - *Initial work* - 

See also the list of [contributors](https://github.com/your/project/contributors) who participated in this project.

## License

## Acknowledgments

* Hat tip to anyone who's code was used
* Inspiration
* etc
