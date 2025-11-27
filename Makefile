# ================= Jensen Agent Makefile =================
PROJECT=jensen-agent
COMPOSE=docker compose -f /volume1/JENSEN/agents/my-agent/docker-compose.yml
ENV=.env

dev:
	@$(COMPOSE) up -d --build
	@echo "Jensen Agent running at https://ccity.synology.me"

logs:
	@$(COMPOSE) logs -f $(PROJECT)

down:
	@$(COMPOSE) down

restart:
	@$(COMPOSE) down && $(COMPOSE) up -d

smoke:
	curl -s -w "\n%{http_code}\n" https://ccity.synology.me/health
	curl -s -w "\n%{http_code}\n" https://ccity.synology.me/version
	curl -s -w "\n%{http_code}\n" -H "X-Agent-Token: $$(grep AGENT_TOKEN $(ENV) | cut -d= -f2)" \
	     -H "Content-Type: application/json" -d '{"message":"smoke"}' https://ccity.synology.me/chat

backup:
	tar czf /volume1/JENSEN/agents/my-agent/backups/jensen-agent-$$(date +%F).tar.gz /volume1/JENSEN/agents/my-agent

restore:
	echo "Place desired tar.gz into backups folder and extract manually."
