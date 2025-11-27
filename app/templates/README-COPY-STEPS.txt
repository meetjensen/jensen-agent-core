Copy these files into your agent's template folder on the NAS.

Destination on NAS host filesystem:
  /volume1/JENSEN/agents/my-agent/app/templates/

Or, copy directly into the running container:
  # from your Mac/SSH shell
  sudo docker cp index.html  jensen-agent:/app/templates/index.html
  sudo docker cp chat.html   jensen-agent:/app/templates/chat.html
  sudo docker cp logs.html   jensen-agent:/app/templates/logs.html

Then restart the container:
  sudo docker restart jensen-agent

Quick tests (adjust host if needed):
  curl -sS https://agent.meetjensen.com/ | head -n 5
  curl -sS https://agent.meetjensen.com/chat | head -n 5
  curl -sS https://agent.meetjensen.com/health
  curl -sS https://agent.meetjensen.com/version
  curl -sS https://agent.meetjensen.com/chat -H "Content-Type: application/json" -H "X-Agent-Token: jensen4254" -d '{"message":"Reply with the single word: PONG"}'
