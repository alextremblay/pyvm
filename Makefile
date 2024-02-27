
test: build/python
	build/python

build/python: build/Lib/sitecustomize.py build/Lib/site-packages
	cd build; cp bin/pypack1 python.zip
	cd build; zip -d python.zip 'Lib/site-packages/*'
	cd build; zip -r python.zip Lib
	mv build/python.zip $@
	touch $@


build/Lib/sitecustomize.py: site_customize_hook.py
	cp site_customize_hook.py $@

build/Lib/site-packages: build/bin/pypack1 pyvm.py
	@echo "setting up site-packages"
	mkdir -p $@
	build/bin/pypack1 -m pip install -t $@ pip
	cp pyvm.py $@/
	touch $@


build/bin/pypack1: build/pypack1.zip
	@echo "Unzipping pypack1.zip"
	unzip build/pypack1.zip bin/pypack1 -d build
	touch $@
	
build/pypack1.zip:
	@echo "Downloading pypack1.zip"
	mkdir build
	wget -O $@ https://github.com/ahgamut/superconfigure/releases/download/z0.0.31/pypack1.zip