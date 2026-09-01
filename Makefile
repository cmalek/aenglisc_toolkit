VERSION = 0.1.0

PACKAGE = aenglisc_toolkit

TECTONIC_VERSION ?= 0.15.0
TECTONIC_RELEASE_BASE ?= https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic@$(TECTONIC_VERSION)
TECTONIC_BUNDLE_URL ?= https://relay.fullyjustified.net/default_bundle_v33.tar
TECTONIC_STAGE_DIR ?= .cache/tectonic-assets
TECTONIC_DOWNLOAD_DIR ?= $(TECTONIC_STAGE_DIR)/downloads
TECTONIC_EXTRACT_DIR ?= $(TECTONIC_STAGE_DIR)/extract
TECTONIC_TARGET_ROOT ?= assets/tectonic
TECTONIC_MACOS_ARM64_ARCHIVE ?= $(TECTONIC_DOWNLOAD_DIR)/tectonic-$(TECTONIC_VERSION)-aarch64-apple-darwin.tar.gz
TECTONIC_MACOS_X86_64_ARCHIVE ?= $(TECTONIC_DOWNLOAD_DIR)/tectonic-$(TECTONIC_VERSION)-x86_64-apple-darwin.tar.gz
TECTONIC_WINDOWS_X86_64_ARCHIVE ?= $(TECTONIC_DOWNLOAD_DIR)/tectonic-$(TECTONIC_VERSION)-x86_64-pc-windows-msvc.zip
TECTONIC_BUNDLE_ARCHIVE ?= $(TECTONIC_DOWNLOAD_DIR)/default_bundle.tar

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

dmg:: ## Create macOS DMG with only the app bundle plus Applications link.
	@command -v create-dmg >/dev/null || { echo "create-dmg not found. Install with: brew install create-dmg"; exit 1; }
	mkdir -p dist/dmg-root
	rm -rf dist/dmg-root/*
	cp -R "dist/Ænglisc Toolkit.app" "dist/dmg-root/"
	create-dmg --volname "Ænglisc Toolkit" --app-drop-link 600 185 "dist/Ænglisc Toolkit.dmg" "dist/dmg-root"

HELP_TOPICS_DIR := oeapp/help/topics
HELP_ASSETS_DIR := oeapp/help/assets
HELP_QCH := $(HELP_ASSETS_DIR)/aenglisc_toolkit_help.qch
HELP_QHC := $(HELP_ASSETS_DIR)/aenglisc_toolkit_help.qhc
HELP_TOPIC_SOURCES := $(wildcard $(HELP_TOPICS_DIR)/*.md)
HELP_SOURCES := $(HELP_TOPIC_SOURCES) scripts/build_help.py oeapp/help/topics.py
# A deleted topic shrinks the wildcard without touching any surviving file, so
# mtime comparison alone would miss it. Encode the topic list as a hash in a
# marker filename: delete or add a topic and the marker no longer exists, which
# makes it newer than the artifacts and forces one rebuild. When the list is
# unchanged the marker already exists and is old, so nothing rebuilds.
HELP_TOPICS_HASH := $(shell ls $(HELP_TOPICS_DIR)/*.md 2>/dev/null | shasum | cut -c1-12)
HELP_MARKER := $(HELP_ASSETS_DIR)/.topics-$(HELP_TOPICS_HASH)

$(HELP_MARKER):
	@mkdir -p $(HELP_ASSETS_DIR)
	@rm -f $(HELP_ASSETS_DIR)/.topics-*
	@touch $@

# GNU Make 3.81 (what macOS ships) has no grouped-target `&:` syntax, so the
# recipe is defined once and attached to both artifacts.
# ponytail: if both artifacts are stale at once the build runs twice; harmless,
# and cheaper than a stamp file that would reintroduce the missing-.qhc bug.
define build_help
	@if [ -x .venv/bin/python ]; then \
		.venv/bin/python scripts/build_help.py; \
	else \
		python scripts/build_help.py; \
	fi
endef

$(HELP_QCH): $(HELP_SOURCES) $(HELP_MARKER)
	$(build_help)

$(HELP_QHC): $(HELP_SOURCES) $(HELP_MARKER)
	$(build_help)

help-assets:: $(HELP_QCH) $(HELP_QHC) ## Build QtHelp assets from markdown help topics (skipped if already up to date).

tectonic-assets-download:: ## Download Tectonic binaries and default bundle to a local cache.
	mkdir -p "$(TECTONIC_DOWNLOAD_DIR)"
	curl -fL "$(TECTONIC_RELEASE_BASE)/tectonic-$(TECTONIC_VERSION)-aarch64-apple-darwin.tar.gz" -o "$(TECTONIC_MACOS_ARM64_ARCHIVE)"
	curl -fL "$(TECTONIC_RELEASE_BASE)/tectonic-$(TECTONIC_VERSION)-x86_64-apple-darwin.tar.gz" -o "$(TECTONIC_MACOS_X86_64_ARCHIVE)"
	curl -fL "$(TECTONIC_RELEASE_BASE)/tectonic-$(TECTONIC_VERSION)-x86_64-pc-windows-msvc.zip" -o "$(TECTONIC_WINDOWS_X86_64_ARCHIVE)"
	curl -fL "$(TECTONIC_BUNDLE_URL)" -o "$(TECTONIC_BUNDLE_ARCHIVE)"

tectonic-assets-extract:: tectonic-assets-download ## Extract downloaded Tectonic archives.
	rm -rf "$(TECTONIC_EXTRACT_DIR)"
	mkdir -p "$(TECTONIC_EXTRACT_DIR)/macos-arm64" "$(TECTONIC_EXTRACT_DIR)/macos-x86_64" "$(TECTONIC_EXTRACT_DIR)/windows-x86_64" "$(TECTONIC_EXTRACT_DIR)/bundle-default"
	tar -xzf "$(TECTONIC_MACOS_ARM64_ARCHIVE)" -C "$(TECTONIC_EXTRACT_DIR)/macos-arm64"
	tar -xzf "$(TECTONIC_MACOS_X86_64_ARCHIVE)" -C "$(TECTONIC_EXTRACT_DIR)/macos-x86_64"
	unzip -q -o "$(TECTONIC_WINDOWS_X86_64_ARCHIVE)" -d "$(TECTONIC_EXTRACT_DIR)/windows-x86_64"
	tar -xf "$(TECTONIC_BUNDLE_ARCHIVE)" -C "$(TECTONIC_EXTRACT_DIR)/bundle-default"
	chmod -R u+rw "$(TECTONIC_EXTRACT_DIR)"

tectonic-assets-prepare:: tectonic-assets-extract ## Copy extracted payloads into assets/tectonic and regenerate manifest.
	@mac_arm_bin=$$(find "$(TECTONIC_EXTRACT_DIR)/macos-arm64" -type f -name tectonic | head -n 1); \
	mac_x86_bin=$$(find "$(TECTONIC_EXTRACT_DIR)/macos-x86_64" -type f -name tectonic | head -n 1); \
	win_x86_bin=$$(find "$(TECTONIC_EXTRACT_DIR)/windows-x86_64" -type f -name tectonic.exe | head -n 1); \
	bundle_dir="$(TECTONIC_EXTRACT_DIR)/bundle-default"; \
	if [ -z "$$mac_arm_bin" ]; then echo "Missing extracted macOS arm64 tectonic binary"; exit 1; fi; \
	if [ -z "$$mac_x86_bin" ]; then echo "Missing extracted macOS x86_64 tectonic binary"; exit 1; fi; \
	if [ -z "$$win_x86_bin" ]; then echo "Missing extracted Windows x86_64 tectonic.exe binary"; exit 1; fi; \
	if [ ! -d "$$bundle_dir" ]; then echo "Missing extracted default bundle directory: $$bundle_dir"; exit 1; fi; \
	python scripts/prepare_tectonic_assets.py \
		--target-root "$(TECTONIC_TARGET_ROOT)" \
		--macos-arm64-binary "$$mac_arm_bin" \
		--macos-x86_64-binary "$$mac_x86_bin" \
		--windows-x86_64-binary "$$win_x86_bin" \
		--bundle-dir "$$bundle_dir"

tectonic-assets-verify:: ## Verify packaged Tectonic assets under assets/tectonic.
	python scripts/verify_tectonic_assets.py --target-root "$(TECTONIC_TARGET_ROOT)"

tectonic-assets:: tectonic-assets-prepare tectonic-assets-verify ## Download, stage, and verify packaged Tectonic assets.
	@echo "Tectonic assets are ready under $(TECTONIC_TARGET_ROOT)"

dev:: help-assets
	exec -a "Ænglisc Toolkit" python -m oeapp.main

show-db::
	ls -la ~/Library/Application\ Support/Ænglisc Toolkit/projects/*.db

backup-db::
	cp ~/Library/Application\ Support/Ænglisc\ Toolkit/projects/default.db .

compile:: sync  ## Run sync to update uv.lock, then rebuild requirements.txt (delete first to ensure all updates are applied).
	rm requirements.txt
	uv pip compile pyproject.toml --group=docs --group=test -o requirements.txt

napoleon-gate:
	@python bin/check_napoleon_gate.py

napoleon-gate-strict:
	@python bin/check_napoleon_gate.py --strict

napoleon-gate-baseline:
	@python bin/check_napoleon_gate.py --write-baseline


help:: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
