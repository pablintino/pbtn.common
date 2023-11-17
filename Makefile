TEST_PROFILE ?= "local"
ISOLATED_ENV ?= true
DEBUG ?= false
define vars
${1}: export PATH=$(PWD)/.venv/bin:$(PATH)
endef

error:
	@echo "Please choose one of the following target: setup_test_env, test_molecule, test_unit, test_sanity"
	@exit 2

.PHONY: setup_test_env
setup_test_env:
ifeq (,$(wildcard ./.venv/bin/python3))
	$(eval $(call vars,$@))
	rm -rf .venv
	python3 -m venv .venv
	pip3 install git+https://github.com/pablintino/ansible-collection-test-runner.git
	ansible-collection-test-runner init
endif

.PHONY: test_molecule
test_molecule: setup_test_env
	$(eval $(call vars,$@))
	ansible-collection-test-runner test \
		--test-types=molecule \
		--profile ${TEST_PROFILE} \
    	$(if $(findstring true,$(ISOLATED_ENV)),--isolated-env,--no-isolated-env) \
		$(if $(TEST_ROLES),--roles=$(TEST_ROLES),) \
		$(if $(TEST_SCENARIOS),--scenarios=$(TEST_SCENARIOS),) \
		$(if $(MOLECULE_CMD),--molecule-command=$(MOLECULE_CMD),) \
		$(if $(findstring true,$(DEBUG)),--debug,)

.PHONY: test_unit
test_unit: setup_test_env
	$(eval $(call vars,$@))
	ansible-collection-test-runner test \
		--profile ${TEST_PROFILE} \
		$(if $(findstring true,$(ISOLATED_ENV)),--isolated-env,--no-isolated-env) \
		$(if $(findstring true,$(DEBUG)),--debug,) \
		--test-types=units

.PHONY: test_sanity
test_sanity: setup_test_env
	$(eval $(call vars,$@))
	ansible-collection-test-runner test \
		--profile ${TEST_PROFILE} \
		$(if $(findstring true,$(ISOLATED_ENV)),--isolated-env,--no-isolated-env) \
		$(if $(findstring true,$(DEBUG)),--debug,) \
		--test-types=sanity
