VERSION = 0.1.0

PACKAGE = aenglisc_toolkit

.DEFAULT_GOAL := help

#======================================================================

clean::
	rm -rf *.tar.gz dist *.egg-info *.rpm
	find . -path './.venv' -prune -o -name "*.pyc" -exec rm '{}' ';'
	find . -path './.venv' -prune -o -name "__pycache__" -exec rm -rf '{}' ';'

dist:: clean
	@uv build --sdist

build:: help-assets
	./build_macos.sh

help-assets:: ## Build QtHelp assets from markdown help topics.
	@if [ -x .venv/bin/python ]; then \
		.venv/bin/python scripts/build_help.py; \
	else \
		python scripts/build_help.py; \
	fi

dev:: help-assets
	exec -a "Ænglisc Toolkit" python -m oeapp.main

show-db::
	ls -la ~/Library/Application\ Support/Ænglisc Toolkit/projects/*.db

backup-db::
	cp ~/Library/Application\ Support/Ænglisc\ Toolkit/projects/default.db .

compile:: sync  ## Run sync to update uv.lock, then rebuild requirements.txt (delete first to ensure all updates are applied).
	rm requirements.txt
	uv pip compile pyproject.toml --group=docs --group=test -o requirements.txt

help:: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

