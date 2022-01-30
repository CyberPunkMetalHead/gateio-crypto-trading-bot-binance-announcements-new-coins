# gateio-trading-bot-binance-announcements
This Gateio x Binance cryptocurrency trading bot scans the Binance Announcements page and picks up on new coin listings.
It then goes to Gateio and places a buy order on the coin that's due to be listed on Binance.
It comes with trailing stop loss, take profit and a test mode.

The idea behind this open source crypto trading algorithm to take advantage of the price spike of new coins as they are being announced for listing on Binance.
As Gateio seems to list many of these coins before Binance does, this exchange is a good place to start.
It comes with a live and test mode so naturally, use at your own risk.

# HOW TO RUN IT
## Simply Run

    Linux:
    bash run.sh

    Windows:
    ./run.bat

## Install dev requirements

    python -m pip install -r dev_requirements.txt

This is necessary make verifying of the code easier and formats the code automatically to match the coding style.

## Install pre-commit hooks

    pre-commit install

This installs the pre-commit git hooks for the project and makes it possible to run the pre-commit script automatically when committing.

## Run Tests and pre-commit scripts manually
### pre-commit checks
To manually run the pre-commit script:

    pre-commit run --all-files

### Tox
Make sure you enabled the virtual environment.
Tox tests the code for multiple environments (3.8, 3.9) and checks code with flake8 and mypy (only on Python Version 3.8).
To run Tox:

        tox

### PyTest
Make sure you enabled the virtual environment.
PyTest runs the unit tests for the code.
To run PyTest:

        python -m pytest


### Flake8
Make sure you enabled the virtual environment.
Flake8 checks the code for errors and warnings.
To run Flake8:

        flake8 src

### Black
Make sure you enabled the virtual environment.
Black formats the code to match the coding style.
To run Black:

        black src



<p>&nbsp;</p>

**For a step-by-step guide on how to set it up and configure please see the guide here:** [Binance new coin trading bot guide](https://www.cryptomaton.org/2021/10/17/a-binance-and-gate-io-crypto-trading-bot-for-new-coin-announcements//)


<p>&nbsp;</p>

**The new coins crypto trading bot explained in more detail.<br>
See the video linked below for an explanation and rationale behind the bot.**

[![binance new coin listings bot](https://img.youtube.com/vi/mIa9eQDhubs/0.jpg)](https://youtu.be/SsSgD0v16Kg)

Want to talk trading bots? Join the discord [https://discord.gg/Ga56KXUUNn](https://discord.gg/Ga56KXUUNn)
