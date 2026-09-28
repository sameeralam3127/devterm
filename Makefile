.PHONY: install uninstall build check lint list demo

install:            ## Interactive install
	./install.sh

uninstall:          ## Remove devterm
	./uninstall.sh

build:              ## Regenerate profiles/ from themes/
	python3 tools/build.py

check:              ## Verify generated files are up to date
	python3 tools/build.py --check

lint:               ## ShellCheck the scripts
	shellcheck -x install.sh uninstall.sh lib/common.sh tools/record-demo.sh

list:               ## List available profiles
	./install.sh --list

demo:               ## Record docs/demo-<theme>.gif (needs vhs + ffmpeg)
	./tools/record-demo.sh
