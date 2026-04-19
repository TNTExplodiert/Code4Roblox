PYTHON ?= python3
PYTHONPATH := src
MISE ?= mise
ROJO_BUILD_OUTPUT := build/CodeRobloxPlugin.rbxm
PLUGIN_FILE_NAME := CodeRobloxPlugin.rbxm
ROBLOX_PLUGIN_DIR ?=
ROBLOX_PLUGIN_OUTPUT := $(if $(ROBLOX_PLUGIN_DIR),$(ROBLOX_PLUGIN_DIR)/$(PLUGIN_FILE_NAME),)

.PHONY: setup install-skill format lint python-test luau-test test build-plugin ci clean

setup:
	@echo "No local bootstrap needed. Ensure python3 and mise are installed."

install-skill:
	@if [ -z "$(CODEX_HOME)" ]; then \
		echo "CODEX_HOME is not set. Export CODEX_HOME first, for example /mnt/c/Users/tom/.codex in WSL."; \
		exit 1; \
	fi
	@mkdir -p "$(CODEX_HOME)"
	@mkdir -p "$(CODEX_HOME)/skills"
	./scripts/install-codex-skill.sh

format:
	$(MISE) trust --yes . >/dev/null && $(MISE) x -- stylua plugin/src plugin/tests

lint:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m compileall src tests scripts
	$(MISE) trust --yes . >/dev/null && $(MISE) x -- stylua --check plugin/src plugin/tests
	$(MISE) trust --yes . >/dev/null && $(MISE) x -- selene plugin/src

python-test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -v

luau-test:
	$(MISE) trust --yes . >/dev/null && $(MISE) x -- lune run plugin/tests/run_tests.luau

test: python-test luau-test

build-plugin:
	mkdir -p build
	$(MISE) trust --yes . >/dev/null && $(MISE) x -- rojo build plugin.project.json --output $(ROJO_BUILD_OUTPUT)
	@if [ -n "$(ROBLOX_PLUGIN_DIR)" ]; then \
		mkdir -p "$(ROBLOX_PLUGIN_DIR)"; \
		cp "$(ROJO_BUILD_OUTPUT)" "$(ROBLOX_PLUGIN_OUTPUT)"; \
		echo "Installed plugin to $(ROBLOX_PLUGIN_OUTPUT)"; \
	else \
		echo "Plugin built at $(ROJO_BUILD_OUTPUT)"; \
		echo "Set ROBLOX_PLUGIN_DIR to auto-install into your local Roblox Plugins folder."; \
	fi

ci: lint test build-plugin

clean:
	rm -rf build __pycache__ .pytest_cache
