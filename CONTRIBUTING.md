If you'd like to start hacking on this project, you'll need to do the following to run the unit tests:

```
# any version of python 3.6+ should work
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r dev.requirements.txt
```

You can then run the unit tests with the `pytest` command.

Additionally, if you want to run the end-to-end tests, you will need to have docker installed.

You can then run all tests, including end-to-end tests, with the `pytest --end-to-end` command.