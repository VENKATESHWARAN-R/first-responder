# Entry point for the testbed. Run `make <target>` from this directory.

CLUSTER  := first-responder
KUBECONFIG := $(or $(TESTBED_KUBECONFIG),$(CURDIR)/.kubeconfig)
export KUBECONFIG
KCTX     := kind-first-responder
NS       := shop
SERVICES := gateway catalog orders payments
VERSION  := 1.3.0
S        ?=

.PHONY: up down build status smoke scenarios inject revert

up:
	./cluster/setup.sh

down:
	./cluster/teardown.sh

## Rebuild app images after code changes, reload them into kind, restart deployments.
build:
	@for svc in $(SERVICES); do \
		docker build -t shop/$$svc:$(VERSION) apps/services/$$svc && \
		kind load docker-image shop/$$svc:$(VERSION) --name $(CLUSTER) && \
		kubectl --context $(KCTX) -n $(NS) rollout restart deploy/$$svc; \
	done

status:
	kubectl --context $(KCTX) -n $(NS) get deploy,pods,svc
	@echo "--- recent events ---"
	@kubectl --context $(KCTX) -n $(NS) get events --sort-by=.lastTimestamp 2>/dev/null | tail -n 15

smoke:
	@echo "GET /api/health"
	@curl -fsS http://localhost:8080/api/health; echo; echo
	@echo "GET /api/products"
	@curl -fsS http://localhost:8080/api/products | head -c 400; echo; echo
	@echo "POST /api/checkout"
	@curl -fsS -X POST -H 'Content-Type: application/json' \
		-d '{"product_id": 1, "quantity": 2}' http://localhost:8080/api/checkout; echo

scenarios:
	@for d in scenarios/[0-9]*/; do \
		id=$$(basename $$d); \
		title=$$(awk -F': ' '/^title:/{print $$2}' $$d/ground-truth.yaml); \
		printf "%-24s %s\n" "$$id" "$$title"; \
	done

inject:
	@test -n "$(S)" || { echo "usage: make inject S=<scenario>, e.g. make inject S=01-bad-deploy"; exit 1; }
	./scenarios/$(S)/inject.sh

revert:
	@test -n "$(S)" || { echo "usage: make revert S=<scenario>"; exit 1; }
	./scenarios/$(S)/revert.sh
