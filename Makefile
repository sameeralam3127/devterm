.PHONY: install uninstall build check lint list demo doctor

install:            ## Interactive install
	./install.sh

uninstall:          ## Remove devterm
	./uninstall.sh

build:              ## Regenerate profiles/ from themes/
	python3 tools/build.py

check:              ## Verify generated files are up to date
	python3 tools/build.py --check

lint:               ## ShellCheck the scripts
	shellcheck -x install.sh uninstall.sh doctor.sh lib/common.sh tools/record-demo.sh

doctor:             ## Check the setup and explain how to fix problems
	./doctor.sh

list:               ## List available profiles
	./install.sh --list

demo:               ## Record docs/demo-<theme>.gif (needs vhs + ffmpeg)
	./tools/record-demo.sh
