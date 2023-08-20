TEST_PROFILE ?= "local"

define vars
${1}: export PATH=$(PWD)/.venv/bin:$(PATH)
endef


.PHONY: setup_test_env
setup_test_env:
ifeq (,$(wildcard ./.venv/bin/python3))
	$(eval $(call vars,$@))
	rm -rf .venv
	python3 -m venv .venv
	pip3 install -r requirements.txt test-requirements.txt
endif

.PHONY: test_molecule
test_molecule: setup_test_env
	$(eval $(call vars,$@))
	./scripts/test-runner --profile ${TEST_PROFILE} \
    	$(if $(TEST_ROLE),--role $(TEST_ROLE),)
