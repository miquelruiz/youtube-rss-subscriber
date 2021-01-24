build:
	python3 setup.py bdist_wheel

upload:
	twine upload --repository testpypi dist/*

clean:
	rm -Rf build dist youtube_rss_subscriber.egg-info
