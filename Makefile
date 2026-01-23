# Makefile for Docker operations

.PHONY: help build-dev build-prod up-dev up-prod down clean logs

# Default target
help:
	@echo "Available commands:"
	@echo "  build-dev    - Build development Docker image"
	@echo "  build-prod   - Build production Docker image"
	@echo "  up-dev       - Start development environment"
	@echo "  up-prod      - Start production environment"
	@echo "  down         - Stop all services"
	@echo "  clean        - Remove all containers and images"
	@echo "  logs         - Show logs from running containers"

# Build development image
build-dev:
	docker build --target development -t interdisciplinary-knowledge-graph:dev .

# Build production image
build-prod:
	docker build --target production -t interdisciplinary-knowledge-graph:latest .

# Start development environment
up-dev:
	docker-compose up --build

# Start production environment
up-prod:
	docker-compose -f docker-compose.prod.yml up -d

# Stop all services
down:
	docker-compose down

# Clean up
clean:
	docker-compose down --rmi all --volumes --remove-orphans
	docker system prune -f

# Show logs
logs:
	docker-compose logs -f

# Show logs for specific service
logs-%:
	docker-compose logs -f $*

# Check service health
health:
	@echo "🔍 检查服务健康状态..."
	@docker-compose ps
	@echo ""
	@echo "🌐 服务状态:"
	@curl -s http://localhost:3000 > /dev/null && echo "✅ 前端: http://localhost:3000" || echo "❌ 前端: 未运行"
	@curl -s http://localhost:8080/health > /dev/null && echo "✅ 后端API: http://localhost:8080" || echo "❌ 后端API: 未运行"
	@curl -s http://localhost:8001/healthz > /dev/null && echo "✅ Agent服务: http://localhost:8001" || echo "❌ Agent服务: 未运行"
	@curl -s http://localhost:7474 > /dev/null && echo "✅ Neo4j: http://localhost:7474" || echo "❌ Neo4j: 未运行"

# Run bash in container
shell-%:
	docker-compose exec $* /bin/bash

# Clean all data (WARNING: This will delete all data!)
clean-all: down
	docker volume rm $$(docker volume ls -q | grep knowledge-graph) 2>/dev/null || true
	docker system prune -f

# Quick start script
quick-start: build-dev up-dev
	@echo "等待服务启动..."
	@sleep 15
	@$(MAKE) health