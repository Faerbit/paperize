all: build

build: clean
	python setup.py sdist bdist_wheel

upload: clean build
	twine upload dist/*

clean:
	rm -rf build dist *.egg-info

