TEST_PROFILE ?= "local"
define vars
${1}: export PATH=$(PWD)/.venv/bin:$(PATH)
endef

error:
	@echo "Please choose one of the following target: setup_test_env, test_molecule, test_unit"
	@exit 2

.PHONY: setup_test_env
setup_test_env:
ifeq (,$(wildcard ./.venv/bin/python3))
	$(eval $(call vars,$@))
	rm -rf .venv
	python3 -m venv .venv
	pip3 install -r requirements.txt
	pip3 install -r test-requirements.txt
endif

.PHONY: test_molecule
test_molecule: setup_test_env
	$(eval $(call vars,$@))
	./scripts/test-runner --profile ${TEST_PROFILE} \
    	$(if $(TEST_ROLE),--role $(TEST_ROLE),) \
		$(if $(MOLECULE_CMD),--molecule-command $(MOLECULE_CMD),)

.PHONY: test_unit
test_unit: setup_test_env
	$(eval $(call vars,$@))
	ansible-test units --requirements -v

.PHONY: test_sanity
test_sanity: setup_test_env
	$(eval $(call vars,$@))
	ansible-test sanity --requirements -v
