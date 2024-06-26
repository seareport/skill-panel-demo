

Panel app made for Heroku CLI

To get started working with Heroku [signup](https://signup.heroku.com) for a free account and [download and install the CLI](https://devcenter.heroku.com/articles/getting-started-with-python#set-up). Once you are set up follow the instructions to log into the CLI.

## Run this app locally

```
panel serve skill_app.py
```

## Deploying this app

1. Clone this repository

2. Modify the `Procfile` which declares which command Heroku should run to serve the app. In this sample app the following command serves the `skill_app.py` example and the websocket origin should match the name of the app on Heroku `skill-app.herokuapp.com` which you will declare in the next step:

```
web: panel serve --address="0.0.0.0" --port=$PORT skill_app.py --allow-websocket-origin=skill-panel.herokuapp.com
```

3. Create a project in heroku


4. Visit the app at skill-app.herokuapp.com


## Modifying the app

In order to serve your own app simply replace the `skill_app.py` with your own Jupyter notebook or Python file declaring a Panel app and then modify the `Procfile` to start that app instead.
