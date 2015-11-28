all:
	virtualenv .virtualenv
	.virtualenv/bin/pip install --upgrade -e .
	.virtualenv/bin/pip install --upgrade -e .[testing]

clean:
	rm -rf .virtualenv

test:
	nosetests
