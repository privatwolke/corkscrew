all:
	virtualenv .virtualenv
	.virtualenv/bin/pip install --upgrade -e .
	.virtualenv/bin/pip install --upgrade -e .[testing]

clean:
	rm -rf .virtualenv
	rm -rf htmlcov
	rm -rf .coverage
	rm nosetests.json

test:
	.virtualenv/bin/nosetests --with-coverage --with-json-extended
	.virtualenv/bin/coverage html
