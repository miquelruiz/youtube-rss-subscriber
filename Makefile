build: setup.py
	python3 setup.py bdist_wheel

upload: build
	twine upload dist/*

clean:
	rm -Rf build dist youtube_rss_subscriber.egg-info
